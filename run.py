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

    # WebSocket/proxy tuning via env vars
    proxy_headers = (os.getenv("PROXY_HEADERS", "true").lower() in ("1", "true", "yes", "on"))
    forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
    try:
        ws_ping_interval = int(os.getenv("WS_PING_INTERVAL", "20"))
    except ValueError:
        ws_ping_interval = 20
    try:
        ws_ping_timeout = int(os.getenv("WS_PING_TIMEOUT", "20"))
    except ValueError:
        ws_ping_timeout = 20
    try:
        ws_max_size = int(os.getenv("WS_MAX_SIZE", "16777216"))  # 16 MiB
    except ValueError:
        ws_max_size = 16777216

    # Note: multiple workers spawn multiple processes; in-memory job state will not be shared.
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        workers=workers,
        proxy_headers=proxy_headers,
        forwarded_allow_ips=forwarded_allow_ips,
        ws_ping_interval=ws_ping_interval,
        ws_ping_timeout=ws_ping_timeout,
        ws_max_size=ws_max_size,
    )
