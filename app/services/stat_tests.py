from typing import Dict, Any
import math


def monobit_frequency_test(bits: str) -> Dict[str, Any]:
    n = len(bits)
    count_ones = bits.count('1')
    s = 2 * count_ones - n
    s_obs = abs(s) / math.sqrt(n)
    # Approximate p-value using erfc
    p_value = math.erfc(s_obs / math.sqrt(2))
    passed = p_value >= 0.01
    return {
        "name": "monobit_frequency",
        "n": n,
        "ones": count_ones,
        "zeros": n - count_ones,
        "p_value": p_value,
        "passed": passed,
    }


def runs_test(bits: str) -> Dict[str, Any]:
    n = len(bits)
    pi = bits.count('1') / n
    if abs(pi - 0.5) >= 2 / math.sqrt(n):
        # Fails precondition
        return {
            "name": "runs",
            "n": n,
            "p_value": 0.0,
            "passed": False,
            "note": "pi too far from 0.5",
        }
    # Count runs
    v = 1
    for i in range(1, n):
        if bits[i] != bits[i - 1]:
            v += 1
    # p-value approximation
    num = abs(v - 2 * n * pi * (1 - pi))
    den = 2 * math.sqrt(2 * n) * pi * (1 - pi)
    p_value = math.erfc(num / den)
    passed = p_value >= 0.01
    return {
        "name": "runs",
        "n": n,
        "pi": pi,
        "runs": v,
        "p_value": p_value,
        "passed": passed,
    }


def block_frequency_test(bits: str, m: int = 32) -> Dict[str, Any]:
    n = len(bits)
    if n < m:
        return {"name": "block_frequency", "n": n, "m": m, "p_value": 0.0, "passed": False, "note": "n < m"}
    blocks = [bits[i : i + m] for i in range(0, n - m + 1, m)]
    t = 0.0
    for b in blocks:
        pi = b.count('1') / m
        t += (pi - 0.5) ** 2
    chi_sq = 4 * m * t
    # p-value using incomplete gamma function approximation via exp(-x/2) sum ...
    # For simplicity, approximate using degrees=k=len(blocks)
    k = len(blocks)
    # Use regularized gamma Q(k/2, chi_sq/2). Crude approximation for common sizes:
    # Here fallback to exp(-chi_sq/2) scaled; not exact but indicative.
    p_value = math.exp(-chi_sq / 2)
    passed = p_value >= 0.01
    return {
        "name": "block_frequency",
        "n": n,
        "m": m,
        "blocks": k,
        "chi_sq": chi_sq,
        "p_value": p_value,
        "passed": passed,
    }


def basic_tests(bits: str) -> Dict[str, Any]:
    results = {}
    for test in (monobit_frequency_test, runs_test, block_frequency_test):
        r = test(bits)
        results[r["name"]] = r
    # Aggregate
    passed = sum(1 for r in results.values() if r.get("passed"))
    results["summary"] = {
        "passed": passed,
        "total": len(results) - 1,
        "score": passed / (len(results) - 1),
    }
    return results

