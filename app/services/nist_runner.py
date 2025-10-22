from __future__ import annotations

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


def run_nist_full(bits: str, emit: Callable[[str, dict], None] | None = None) -> Dict[str, Any]:
    logger = StageLogger(emit)
    started_at = time.time()
    logger.stage("nist:start", {"length": len(bits)})

    seq = _bits_to_np_array(bits)
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
        "length": int(len(bits)),
        "tests": tests,
        "summary": summary,
        "stages": logger.events,
    }

