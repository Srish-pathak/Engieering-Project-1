"""
TechSpecAnalyser — Complexity and Maintainability Analysis.
Integrates Radon (McCabe CC & Halstead MI) and Lizard.
Preserves existing API contract: analyze_complexity(code, language).
"""
from typing import Any, Dict

from analyzers.static_analysis import get_analyzer

RANK_LABELS = {
    "A": "Simple, low risk (1-5)",
    "B": "Moderate, well structured (6-10)",
    "C": "Complex, consider splitting (11-20)",
    "D": "Very complex, hard to test (21-30)",
    "E": "Extremely complex (31-40)",
    "F": "Unmaintainable, refactor now (41+)",
}


def analyze_complexity(code: str, language: str, file_path: str = "") -> Dict[str, Any]:
    """
    Computes McCabe Cyclomatic Complexity, Halstead Maintainability Index,
    and function-level rankings.
    """
    if not code or not code.strip():
        return {
            "average_complexity": 0.0,
            "rating": "N/A",
            "maintainability_index": 100.0,
            "maintainability_rank": "A",
            "blocks": [],
            "error": "Empty code provided",
        }

    analyzer = get_analyzer(language)
    return analyzer.calculate_complexity(code, file_path)
