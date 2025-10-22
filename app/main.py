import asyncio
import time
import uuid
from typing import Dict, Any, Callable, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Body
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    DrawConfig,
    DrawStartResponse,
    DrawResult,
    AuditInput,
    AuditResult,
    DemoConfig,
    NistStartResponse,
    NistReport,
)
from app.services.generator import run_draw
from app.services.logging import StageLogger
from app.services.stat_tests import basic_tests
from app.utils.sse import sse_format
from app.services.nist_runner import run_nist_full

# OpenAPI/Swagger metadata
tags_metadata = [
    {
        "name": "Draw",
        "description": "Генерация тиража: сбор энтропии, обработка, слепок, тесты и результат."
    },
    {
        "name": "Audit",
        "description": "Аудит внешних последовательностей по базовым статистическим критериям."
    },
    {"name": "Demo", "description": "Демонстрационный режим с пояснениями этапов в реальном времени."},
    {"name": "Health", "description": "Технические эндпоинты и корень сервиса."},
]

app = FastAPI(
    title="Loto RNG Service",
    version="0.1.0",
    description=(
        "Сервис генерации тиражей и аудита случайных последовательностей.\n\n"
        "Сценарии: 1) Тираж с онлайн‑процессом и автотестами; "
        "2) Аудит внешнего генератора; 3) Демонстрационный режим."
    ),
    contact={
        "name": "Hackathon Loto 2025",
        "url": "https://example.org",
    },
    openapi_tags=tags_metadata,
    docs_url="/swagger",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


JOBS: Dict[str, Dict[str, Any]] = {}
NIST_JOBS: Dict[str, Dict[str, Any]] = {}


@app.get("/health", tags=["Health"], summary="Проверка доступности сервиса")
async def health():
    return {"status": "ok", "time": time.time()}


@app.post(
    "/draw/start",
    response_model=DrawStartResponse,
    tags=["Draw"],
    summary="Запуск генерации тиража",
    description=(
        "Инициирует генерацию: сбор энтропии из указанных источников, вайтинг, "
        "формирование сид‑значения и комбинации. Результаты этапов доступны через SSE."
    ),
)
async def start_draw(
    cfg: DrawConfig = Body(
        ...,
        examples={
            "default": {
                "summary": "Полный набор источников",
                "value": {
                    "sources": ["news", "weather", "os", "time"],
                    "bits": 4096,
                    "numbers": 6,
                    "max_number": 49,
                },
            }
        },
    )
):
    job_id = str(uuid.uuid4())
    # place holder job
    JOBS[job_id] = {
        "status": "running",
        "config": cfg.model_dump(),
        "started_at": time.time(),
        "stages": [],
    }

    async def run():
        def emit(name: str, evt: dict):
            JOBS[job_id]["stages"].append(evt)

        try:
            result = run_draw(
                sources=cfg.sources,
                bits=cfg.bits,
                numbers=cfg.numbers,
                max_number=cfg.max_number,
                emit=emit,
            )
            JOBS[job_id].update(result)
        except Exception as e:
            JOBS[job_id].update({"status": "error", "error": str(e), "finished_at": time.time()})

    asyncio.create_task(run())
    return DrawStartResponse(job_id=job_id)


@app.get(
    "/draw/result/{job_id}",
    response_model=DrawResult,
    tags=["Draw"],
    summary="Получение результата тиража",
    description="Возвращает статус задания, этапы, комбинацию, слепок и результаты автотестов.",
)
async def draw_result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    data = {
        "job_id": job_id,
        "status": job.get("status", "running"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "config": job.get("config"),
        "stages": job.get("stages", []),
        "draw": job.get("draw"),
        "fingerprint": job.get("fingerprint"),
        "tests": job.get("tests"),
    }
    return JSONResponse(data)


@app.get(
    "/draw/stream/{job_id}",
    tags=["Draw"],
    summary="SSE‑стрим этапов генерации",
    description=(
        "Серверные события (text/event-stream) с этапами: entropy, whitening, seed, draw, tests, final. "
        "Удобно просматривать в браузере или через curl -N."
    ),
    responses={
        200: {
            "content": {"text/event-stream": {"example": "event: entropy:start\ndata: {\"min_bits\":4096}\n\n"}},
            "description": "Поток серверных событий",
        }
    },
)
async def draw_stream(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")

    async def event_gen():
        idx = 0
        # keep streaming as long as running
        while True:
            job = JOBS.get(job_id)
            if not job:
                break
            stages = job.get("stages", [])
            while idx < len(stages):
                evt = stages[idx]
                idx += 1
                yield sse_format(evt.get("stage", "stage"), evt)
            if job.get("status") in ("completed", "error"):
                # send final
                tests_obj = job.get("tests", {}) or {}
                nist_summary = tests_obj.get("nist", {}).get("summary", {}) if isinstance(tests_obj, dict) else {}
                yield sse_format("final", {"status": job.get("status"), "result": {
                    "draw": job.get("draw"), "fingerprint": job.get("fingerprint"), "tests": nist_summary
                }})
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get(
    "/draw/bits/{job_id}",
    tags=["Draw"],
    summary="Получение использованного битового потока",
    description="Возвращает белёные биты, использованные для генерации (для внешнего аудита).",
)
async def draw_bits(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.get("status") != "completed":
        raise HTTPException(400, "job not completed yet")
    bits = job.get("_white_bits")
    if not bits:
        raise HTTPException(404, "no bits available")
    return JSONResponse({"job_id": job_id, "bits": bits, "length": len(bits)})


@app.post(
    "/audit/analyze",
    response_model=AuditResult,
    tags=["Audit"],
    summary="Анализ последовательности",
    description=(
        "Принимает битовую строку (0/1) или список чисел, конвертирует в битовый поток и проводит базовые тесты."
    ),
)
async def audit_analyze(
    payload: AuditInput = Body(
        ...,
        examples={
            "bits": {"summary": "Биты", "value": {"sequence_bits": "010011001101..."}},
            "numbers": {"summary": "Числа", "value": {"numbers": [12, 7, 33, 45, 3]}}
        },
    )
):
    bits: Optional[str] = None
    if payload.sequence_bits:
        bits = ''.join(ch for ch in payload.sequence_bits if ch in '01')
    elif payload.numbers is not None:
        # convert numbers to bits by concatenating fixed-width binary representations
        if not payload.numbers:
            raise HTTPException(400, "numbers is empty")
        width = max(1, max(payload.numbers).bit_length())
        bits = ''.join(f"{n:0{width}b}" for n in payload.numbers)
    else:
        raise HTTPException(400, "Provide sequence_bits or numbers")
    results = basic_tests(bits)
    return AuditResult(status="ok", length=len(bits), tests=results)


@app.post(
    "/audit/upload",
    response_model=AuditResult,
    tags=["Audit"],
    summary="Аудит файла с битами",
    description="Загружает файл, извлекает биты 0/1 и проводит базовые тесты.",
)
async def audit_upload(file: UploadFile = File(...)):
    content = (await file.read()).decode('utf-8', errors='ignore')
    bits = ''.join(ch for ch in content if ch in '01')
    if not bits:
        raise HTTPException(400, "Uploaded file does not contain 0/1 bits")
    results = basic_tests(bits)
    return AuditResult(status="ok", length=len(bits), tests=results)


# NIST SP 800-22 full battery
@app.post(
    "/audit/nist/start",
    response_model=NistStartResponse,
    tags=["Audit"],
    summary="Запуск полного набора NIST SP 800-22",
    description=(
        "Принимает битовую строку или список чисел и запускает полный набор тестов NIST. "
        "Возвращает идентификатор задачи для отслеживания прогресса и результата."
    ),
)
async def nist_start(payload: AuditInput = Body(...)):
    # Prepare bits
    bits: Optional[str] = None
    if payload.sequence_bits:
        bits = ''.join(ch for ch in payload.sequence_bits if ch in '01')
    elif payload.numbers is not None:
        if not payload.numbers:
            raise HTTPException(400, "numbers is empty")
        width = max(1, max(payload.numbers).bit_length())
        bits = ''.join(f"{n:0{width}b}" for n in payload.numbers)
    else:
        raise HTTPException(400, "Provide sequence_bits or numbers")

    job_id = str(uuid.uuid4())
    NIST_JOBS[job_id] = {"status": "running", "started_at": time.time(), "stages": []}

    async def run():
        def emit(name: str, evt: dict):
            NIST_JOBS[job_id]["stages"].append(evt)

        try:
            result = run_nist_full(bits, emit=emit)
            NIST_JOBS[job_id].update(result)
        except Exception as e:
            NIST_JOBS[job_id].update({"status": "error", "error": str(e), "finished_at": time.time()})

    asyncio.create_task(run())
    return NistStartResponse(job_id=job_id)


@app.get(
    "/audit/nist/result/{job_id}",
    response_model=NistReport,
    tags=["Audit"],
    summary="Результат полного набора NIST",
)
async def nist_result(job_id: str):
    job = NIST_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    data = {
        "job_id": job_id,
        "status": job.get("status", "running"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "length": job.get("length", 0),
        "tests": job.get("tests", []),
        "summary": job.get("summary", {"eligible": 0, "total": 0, "passed": 0, "ratio": 0.0}),
    }
    return JSONResponse(data)


@app.get(
    "/audit/nist/stream/{job_id}",
    tags=["Audit"],
    summary="SSE прогресс NIST тестов",
    description="Стрим серверных событий с этапами выполнения полного набора NIST.",
)
async def nist_stream(job_id: str):
    job = NIST_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")

    async def event_gen():
        idx = 0
        while True:
            job = NIST_JOBS.get(job_id)
            if not job:
                break
            stages = job.get("stages", [])
            while idx < len(stages):
                evt = stages[idx]
                idx += 1
                yield sse_format(evt.get("stage", "nist"), evt)
            if job.get("status") in ("completed", "error"):
                yield sse_format("final", {"status": job.get("status"), "summary": job.get("summary", {})})
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post(
    "/draw/{job_id}/nist/start",
    response_model=NistStartResponse,
    tags=["Draw"],
    summary="Запуск NIST тестов на биты тиража",
)
async def nist_from_draw(job_id: str):
    job = JOBS.get(job_id)
    if not job or job.get("status") != "completed":
        raise HTTPException(400, "draw job not found or not completed")
    bits = job.get("_white_bits")
    if not bits:
        raise HTTPException(404, "no bits available for this draw")

    n_job_id = str(uuid.uuid4())
    NIST_JOBS[n_job_id] = {"status": "running", "started_at": time.time(), "stages": []}

    async def run():
        def emit(name: str, evt: dict):
            NIST_JOBS[n_job_id]["stages"].append(evt)

        try:
            result = run_nist_full(bits, emit=emit)
            NIST_JOBS[n_job_id].update(result)
        except Exception as e:
            NIST_JOBS[n_job_id].update({"status": "error", "error": str(e), "finished_at": time.time()})

    asyncio.create_task(run())
    return NistStartResponse(job_id=n_job_id)


@app.get(
    "/demo/stream",
    tags=["Demo"],
    summary="Демо‑пояснения в реальном времени",
    description="Поток серверных событий с пояснениями ключевых этапов работы системы.",
)
async def demo_stream(scenario: str = "default"):
    async def gen():
        messages = [
            ("demo:start", {"scenario": scenario, "info": "Демонстрационный режим. Поясняем этапы."}),
            ("demo:entropy", {"info": "Сбор энтропии из RSS, погодных данных и ОС."}),
            ("demo:whitening", {"info": "Вайтинг (экстрактор фон Неймана) убирает смещения."}),
            ("demo:seed", {"info": "Производная из битов — криптографический seed и слепок."}),
            ("demo:draw", {"info": "Генерируем комбинацию без смещения методом выборки."}),
            ("demo:tests", {"info": "Полный набор тестов NIST запускается автоматически."}),
            ("demo:finish", {"info": "Готово. Слепок можно использовать для верификации."}),
        ]
        for ev, data in messages:
            yield sse_format(ev, data)
            await asyncio.sleep(0.6)
    return StreamingResponse(gen(), media_type="text/event-stream")


# Convenience root
@app.get("/", tags=["Health"], summary="Корень сервиса")
async def root():
    return {"service": app.title, "version": app.version, "endpoints": [
        "/draw/start", "/draw/result/{job_id}", "/draw/stream/{job_id}", "/audit/analyze", "/audit/upload", "/demo/stream", "/health"
    ]}


 
