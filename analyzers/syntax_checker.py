"""
TechSpecAnalyser — Syntax Validation Engine.
Multi-language syntax gate routing to language adapters.
Preserves existing API contract: check_syntax(code, language).
"""
from typing import Any, Dict

from analyzers.static_analysis import get_analyzer


def check_syntax(code: str, language: str, file_path: str = "") -> Dict[str, Any]:
    """
    Validates code syntax for the specified language.
    Returns: {"valid": bool, "bugs": List[Dict], "checker": str}
    """
    if not code or not code.strip():
        return {"valid": True, "bugs": [], "checker": "empty-check"}

    analyzer = get_analyzer(language)
    return analyzer.check_syntax(code, file_path)
