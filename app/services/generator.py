import json
import random
import time
from typing import Dict, Any, Callable

from .logging import StageLogger
from .entropy import collect_entropy, von_neumann_extractor, derive_seed_and_commitment
from .nist_runner import run_nist_full


def run_draw(
    sources: list[str],
    bits: int,
    numbers: int,
    max_number: int,
    emit: Callable[[str, dict], None] | None = None,
) -> Dict[str, Any]:
    logger = StageLogger(emit)
    started_at = time.time()
    # 1) Collect whitened entropy to an exact target length
    target_white_bits = bits
    white_bits_parts: list[str] = []
    total_white = 0
    # Start with a reasonable pre-whitening batch; adjust if shortfall
    batch_raw = max(4096, target_white_bits * 2)
    while total_white < target_white_bits:
        raw_bits = collect_entropy(sources, batch_raw, logger)
        chunk = von_neumann_extractor(raw_bits, logger)
        white_bits_parts.append(chunk)
        total_white += len(chunk)
        if total_white < target_white_bits:
            logger.stage(
                "whitening:shortfall",
                {"have": total_white, "need": target_white_bits, "next_batch": batch_raw * 2},
            )
            # Increase batch size to converge faster
            batch_raw = min(batch_raw * 2, max(65536, target_white_bits * 16))
    white_bits = ("".join(white_bits_parts))[:target_white_bits]
    # 3) Derive seed and commitment
    seed_bytes, fingerprint = derive_seed_and_commitment(white_bits, logger)
    # 4) Generate draw
    logger.stage("draw:start", {"numbers": numbers, "max": max_number})
    seed_int = int.from_bytes(seed_bytes, 'big')
    rng = random.Random(seed_int)
    combo = sorted(rng.sample(range(1, max_number + 1), k=numbers))
    logger.stage("draw:done", {"combo": combo})
    # 5) Full NIST SP 800-22 tests
    logger.stage("tests:start", {"suite": "NIST SP 800-22"})
    nist = run_nist_full(white_bits)
    # Merge NIST stages into draw timeline
    for evt in nist.get("stages", []):
        logger.stage(evt.get("stage", "nist"), evt.get("data", {}))
    logger.stage("tests:done", {"suite": "NIST SP 800-22", "summary": nist.get("summary", {})})
    finished_at = time.time()
    return {
        "status": "completed",
        "started_at": started_at,
        "finished_at": finished_at,
        "stages": logger.events,
        "draw": combo,
        "fingerprint": fingerprint,
        "tests": {"nist": {"summary": nist.get("summary", {}), "tests": nist.get("tests", [])}},
        "_white_bits": white_bits,
    }
