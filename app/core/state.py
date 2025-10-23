from typing import Dict, Any
import threading

# Global in-memory job registries
JOBS: Dict[str, Dict[str, Any]] = {}
NIST_JOBS: Dict[str, Dict[str, Any]] = {}

# Global locks to protect shared state from multi-thread updates
JOBS_LOCK = threading.RLock()
NIST_JOBS_LOCK = threading.RLock()
