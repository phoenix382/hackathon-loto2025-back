import asyncio
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Body, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.state import NIST_JOBS
from app.domain.schemas import AuditInput, AuditResult, NistStartResponse, NistReport
from app.services.stat_tests import basic_tests
from app.services.nist_runner import run_nist_full
from app.utils.sse import sse_format


router = APIRouter()


@router.post(
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
        if not payload.numbers:
            raise HTTPException(400, "numbers is empty")
        width = max(1, max(payload.numbers).bit_length())
        bits = ''.join(f"{n:0{width}b}" for n in payload.numbers)
    else:
        raise HTTPException(400, "Provide sequence_bits or numbers")
    results = basic_tests(bits)
    return AuditResult(status="ok", length=len(bits), tests=results)


@router.post(
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


@router.post(
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


@router.get(
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


@router.get(
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

