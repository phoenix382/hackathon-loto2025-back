import time
from fastapi import APIRouter


router = APIRouter()


@router.get("/health", tags=["Health"], summary="Проверка доступности сервиса")
async def health():
    return {"status": "ok", "time": time.time()}


@router.get("/", tags=["Health"], summary="Корень сервиса")
async def root():
    return {
        "service": "Loto RNG Service",
        "version": "0.1.0",
        "endpoints": [
            "/draw/start",
            "/draw/result/{job_id}",
            "/draw/stream/{job_id}",
            "/draw/ws/{job_id}",
            "/draw/ws-info/{job_id}",
            "/draw/bits/{job_id}",
            "/audit/analyze",
            "/audit/upload",
            "/audit/nist/start",
            "/audit/nist/stream/{job_id}",
            "/audit/nist/ws/{job_id}",
            "/audit/nist/ws-info/{job_id}",
            "/audit/nist/result/{job_id}",
            "/demo/stream",
            "/health",
        ],
    }
