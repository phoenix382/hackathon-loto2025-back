import os
import sys
import uvicorn

# Ensure local vendored NistRng (lib/NistRng) is importable as top-level 'nistrng'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VENDOR_DIR = os.path.join(BASE_DIR, 'lib', 'NistRng')
if os.path.isdir(VENDOR_DIR) and VENDOR_DIR not in sys.path:
    sys.path.insert(0, VENDOR_DIR)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
