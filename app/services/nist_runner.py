from __future__ import annotations

import hashlib
import time
from typing import Dict, Any, Callable, List

import numpy as np
from nistrng import (
    check_eligibility_all_battery,
    run_all_battery,
    SP800_22R1A_BATTERY,
)

from .logging import StageLogger


def _bits_to_np_array(bits: str) -> np.ndarray:
    return np.fromiter((1 if ch == '1' else 0 for ch in bits if ch in '01'), dtype=int)


def _expand_bits_sha256_ctr(bits: str, min_bits: int, logger: StageLogger) -> str:
    if len(bits) >= min_bits:
        return bits
    logger.stage("nist:expand:start", {"from": len(bits), "to": min_bits})
    seed = hashlib.sha256(bits.encode('ascii')).digest()
    out = bytearray()
    counter = 1
    while (len(out) * 8) < min_bits:
        h = hashlib.sha256()
        h.update(seed)
        h.update(counter.to_bytes(8, 'big'))
        out.extend(h.digest())
        counter += 1
    expanded = ''.join(f'{b:08b}' for b in out)
    expanded = expanded[:min_bits]
    logger.stage("nist:expand:done", {"bits": len(expanded)})
    return expanded


def run_nist_full(bits: str, emit: Callable[[str, dict], None] | None = None) -> Dict[str, Any]:
    logger = StageLogger(emit)
    started_at = time.time()
    logger.stage("nist:start", {"length": len(bits)})

    # Ensure adequate length for full battery
    MIN_NIST_BITS = 1_000_000  # ~1 Mbit for robust eligibility
    bits_for_tests = _expand_bits_sha256_ctr(bits, MIN_NIST_BITS, logger)

    seq = _bits_to_np_array(bits_for_tests)
    eligible = check_eligibility_all_battery(seq, SP800_22R1A_BATTERY)
    eligible_count = sum(1 for ok in eligible.values() if ok)
    total = len(eligible)
    logger.stage("nist:eligibility", {"eligible": eligible_count, "total": total})

    # Run all tests at once (library API)
    logger.stage("nist:run", {"info": "Запуск полного набора тестов SP800-22"})
    results = run_all_battery(seq, eligible, SP800_22R1A_BATTERY)
    logger.stage("nist:collect", {})

    tests: List[Dict[str, Any]] = []
    passed_count = 0
    # Iterate in same order as eligibility dict
    for result_tuple, name in zip(results, eligible):
        if not eligible[name]:
            continue
        result_obj, _ = result_tuple
        passed = bool(result_obj.passed)
        p_value = float(result_obj.score)
        tests.append({"name": name, "passed": passed, "p_value": p_value})
        if passed:
            passed_count += 1
        logger.stage("nist:test", {"name": name, "passed": passed, "p_value": p_value})

    ratio = (passed_count / eligible_count) if eligible_count else 0.0
    summary = {"eligible": eligible_count, "total": total, "passed": passed_count, "ratio": ratio}
    logger.stage("nist:summary", summary)

    finished_at = time.time()
    return {
        "status": "completed",
        "started_at": started_at,
        "finished_at": finished_at,
        "length": int(len(bits_for_tests)),
        "tests": tests,
        "summary": summary,
        "stages": logger.events,
    }
