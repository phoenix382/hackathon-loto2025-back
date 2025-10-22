import asyncio
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.state import JOBS, NIST_JOBS
from app.domain.schemas import DrawConfig, DrawStartResponse, DrawResult, NistStartResponse
from app.services.generator import run_draw
from app.services.nist_runner import run_nist_full
from app.utils.sse import sse_format


router = APIRouter()


@router.post(
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


@router.get(
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


@router.get(
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
                tests_obj = job.get("tests", {}) or {}
                nist_summary = tests_obj.get("nist", {}).get("summary", {}) if isinstance(tests_obj, dict) else {}
                yield sse_format("final", {"status": job.get("status"), "result": {
                    "draw": job.get("draw"), "fingerprint": job.get("fingerprint"), "tests": nist_summary
                }})
                break
            await asyncio.sleep(0.2)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get(
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


@router.post(
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

