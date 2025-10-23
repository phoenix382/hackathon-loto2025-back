from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.tags import tags_metadata
from app.routers.draw import router as draw_router
from app.routers.audit import router as audit_router
from app.routers.demo import router as demo_router
from app.routers.health import router as health_router
from app.core.concurrency import init_default_executor, shutdown_default_executor


app = FastAPI(
    title="Loto RNG Service",
    version="0.1.0",
    description=(
        "Сервис генерации тиражей и аудита случайных последовательностей.\n\n"
        "Сценарии: 1) Тираж с онлайн‑процессом и полным NIST; "
        "2) Аудит внешнего генератора; 3) Демонстрационный режим."
    ),
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

@app.on_event("startup")
async def _startup():
    # Configure a larger default thread pool for blocking tasks
    init_default_executor()


@app.on_event("shutdown")
async def _shutdown():
    shutdown_default_executor()


# Routers
app.include_router(draw_router)
app.include_router(audit_router)
app.include_router(demo_router)
app.include_router(health_router)
