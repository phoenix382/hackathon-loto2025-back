import json
from typing import Any, Dict, Iterable


def sse_format(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\n" f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def sse_stream(generator: Iterable[tuple[str, Dict[str, Any]]]):
    for event, data in generator:
        yield sse_format(event, data)

