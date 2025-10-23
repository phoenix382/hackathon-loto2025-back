import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.utils.sse import sse_format


router = APIRouter()


@router.get(
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


@router.websocket("/demo/ws")
async def demo_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        scenario = websocket.query_params.get("scenario", "default")
        # immediate ack
        await websocket.send_json({"event": "ready", "data": {"scenario": scenario}})

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
            await websocket.send_json({"event": ev, "data": {"stage": ev, "data": data, "time": 0.0}})
            await asyncio.sleep(0.6)
        await websocket.send_json({"event": "final", "data": {"status": "completed"}})
    except WebSocketDisconnect:
        pass
