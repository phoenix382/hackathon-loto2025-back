import json
import random
import time
from typing import Dict, Any, Callable

from .logging import StageLogger
from .entropy import collect_entropy, von_neumann_extractor, derive_seed_and_commitment
from .stat_tests import basic_tests


def run_draw(
    sources: list[str],
    bits: int,
    numbers: int,
    max_number: int,
    emit: Callable[[str, dict], None] | None = None,
) -> Dict[str, Any]:
    logger = StageLogger(emit)
    started_at = time.time()
    # 1) Collect entropy
    raw_bits = collect_entropy(sources, bits, logger)
    # 2) Whitening
    white_bits = von_neumann_extractor(raw_bits, logger)
    if len(white_bits) < numbers * 12:  # ensure enough material
        # Pad deterministically from raw
        logger.stage("whitening:pad", {"from": len(white_bits)})
        white_bits += raw_bits[: numbers * 12]
        logger.stage("whitening:padded", {"to": len(white_bits)})
    # 3) Derive seed and commitment
    seed_bytes, fingerprint = derive_seed_and_commitment(white_bits, logger)
    # 4) Generate draw
    logger.stage("draw:start", {"numbers": numbers, "max": max_number})
    seed_int = int.from_bytes(seed_bytes, 'big')
    rng = random.Random(seed_int)
    combo = sorted(rng.sample(range(1, max_number + 1), k=numbers))
    logger.stage("draw:done", {"combo": combo})
    # 5) Basic randomness tests
    logger.stage("tests:start", {})
    tests = basic_tests(white_bits[: max(2048, numbers * 64)])
    logger.stage("tests:done", {"summary": tests.get("summary", {})})
    finished_at = time.time()
    return {
        "status": "completed",
        "started_at": started_at,
        "finished_at": finished_at,
        "stages": logger.events,
        "draw": combo,
        "fingerprint": fingerprint,
        "tests": tests,
        "_white_bits": white_bits,
    }
