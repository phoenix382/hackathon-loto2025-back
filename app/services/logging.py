from typing import Any, Dict, Callable
import time


class StageLogger:
    def __init__(self, emit: Callable[[str, Dict[str, Any]], None] | None = None):
        self.events: list[dict[str, Any]] = []
        self.emit = emit
        self.t0 = time.time()

    def stage(self, name: str, payload: Dict[str, Any]):
        evt = {
            "time": time.time() - self.t0,
            "stage": name,
            "data": payload,
        }
        self.events.append(evt)
        if self.emit:
            try:
                self.emit(name, evt)
            except Exception:
                pass

