import os
import sys
import uvicorn

# Ensure local vendored NistRng (lib/NistRng) is importable as top-level 'nistrng'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VENDOR_DIR = os.path.join(BASE_DIR, 'lib', 'NistRng')
if os.path.isdir(VENDOR_DIR) and VENDOR_DIR not in sys.path:
    sys.path.insert(0, VENDOR_DIR)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers_env = os.getenv("UVICORN_WORKERS") or os.getenv("WEB_CONCURRENCY")
    workers = int(workers_env) if workers_env and workers_env.isdigit() else 1
    # Note: multiple workers spawn multiple processes; in-memory job state will not be shared.
    uvicorn.run("app.main:app", host=host, port=port, reload=False, workers=workers)
