import re
from typing import Any

try:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit
except ImportError:  # radon is optional at import time
    cc_visit = mi_visit = None


def analyze_complexity(code: str, language: str) -> dict[str, Any]:
    """Radon for Python, a simple branch/nesting heuristic for everything else."""
    if language == "Python" and cc_visit is not None:
        return _analyze_python(code)
    return _analyze_heuristic(code)


def _analyze_python(code: str) -> dict[str, Any]:
    try:
        blocks = cc_visit(code)
    except SyntaxError as exc:
        return {"method": "radon", "average_complexity": 0, "rating": "N/A", "details": [],
                "maintainability_index": None, "error": "Syntax error, could not analyze: {}".format(exc)}
    if not blocks:
        return {"method": "radon", "average_complexity": 1, "rating": "A", "details": [],
                "maintainability_index": _safe_mi(code)}
    details = [{"name": b.name, "complexity": b.complexity, "rank": _rank_letter(b.complexity)} for b in blocks]
    average = sum(b.complexity for b in blocks) / len(blocks)
    return {"method": "radon", "average_complexity": round(average, 2), "rating": _rank_letter(average),
            "details": details, "maintainability_index": _safe_mi(code)}


def _safe_mi(code: str) -> float | None:
    try:
        return round(mi_visit(code, multi=True), 2)
    except Exception:
        return None


def _rank_letter(complexity: float) -> str:
    for limit, letter in ((5, "A"), (10, "B"), (20, "C"), (30, "D"), (40, "E")):
        if complexity <= limit:
            return letter
    return "F"


def _analyze_heuristic(code: str) -> dict[str, Any]:
    branches = len(re.findall(r"\b(if|for|while|case|catch|switch)\b", code))
    depth = max_depth = 0
    for char in code:
        if char == "{":
            depth += 1
            max_depth = max(max_depth, depth)
        elif char == "}":
            depth = max(0, depth - 1)
    estimate = 1 + branches + max_depth * 0.5
    rating = "Low" if estimate <= 5 else "Medium" if estimate <= 12 else "High"
    return {
        "method": "heuristic", "average_complexity": round(estimate, 2), "rating": rating,
        "details": [
            {"name": "branch_count", "complexity": branches, "rank": "-"},
            {"name": "max_nesting_depth", "complexity": max_depth, "rank": "-"},
        ],
        "maintainability_index": None,
    }
