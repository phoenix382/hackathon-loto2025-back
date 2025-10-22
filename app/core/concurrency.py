import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

_executor: Optional[ThreadPoolExecutor] = None


def init_default_executor() -> None:
    """Initialize and set loop's default ThreadPoolExecutor.

    Max workers can be configured via env var THREAD_POOL_WORKERS.
    """
    global _executor
    if _executor is not None:
        return
    try:
        max_workers = int(os.getenv("THREAD_POOL_WORKERS", "0"))
    except ValueError:
        max_workers = 0
    if max_workers <= 0:
        # Sensible default: CPU * 4, min 8, max 64
        cpu = os.cpu_count() or 2
        max_workers = max(8, min(64, cpu * 4))
    loop = asyncio.get_event_loop()
    _executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="app-worker")
    loop.set_default_executor(_executor)


def shutdown_default_executor() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None

