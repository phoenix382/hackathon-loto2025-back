from __future__ import annotations

import hashlib
import time
from typing import Dict, Any, Callable, List

import numpy as np
from lib.NistRng.nistrng import (
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

    bits_for_tests = bits

    seq = _bits_to_np_array(bits_for_tests)
    eligible = check_eligibility_all_battery(seq, SP800_22R1A_BATTERY)
    eligible_count = sum(1 for ok in eligible.values() if ok)
    total = len(eligible)
    logger.stage("nist:eligibility", {"eligible": eligible_count, "total": total})

    # Run all tests at once (library API)
    logger.stage("nist:run", {"info": "Запуск полного набора тестов SP800-22"})
    # Disabled full-battery run due to defects; running per-test below
    results = []
    logger.stage("nist:collect", {})

    tests: List[Dict[str, Any]] = []
    passed_count = 0
    eligible_names = [name for name, ok in eligible.items() if ok]
    for name in eligible_names:
        logger.stage("nist:run:test", {"name": name})
        fresh_seq = _bits_to_np_array(bits_for_tests)
        single_battery = {name: SP800_22R1A_BATTERY[name]}
        single_eligible = {name: True}
        try:
            single_results = run_all_battery(fresh_seq, single_eligible, single_battery)
        except Exception as e:
            logger.stage("nist:test:error", {"name": name, "error": str(e)})
            continue
        for result_obj, elapsed_ms in single_results:
            passed = bool(result_obj.passed)
            p_value = float(result_obj.score)
            tests.append({"name": name, "passed": passed, "p_value": p_value})
            if passed:
                passed_count += 1
            logger.stage("nist:test", {"name": name, "passed": passed, "p_value": p_value, "elapsed_ms": elapsed_ms})

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
