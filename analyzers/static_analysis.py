"""
TechSpecAnalyser — Unified Multi-Language Static Analysis Dispatcher.
Routes code to language adapters (Python, C, C++, Java, JS, TS, HTML, CSS).
Preserves existing API contract: analyze_static(code, language).
"""
from typing import Any, Dict, List

from analyzers.cpp_analyzer import CppAnalyzer
from analyzers.java_analyzer import JavaAnalyzer
from analyzers.javascript_analyzer import JavaScriptAnalyzer
from analyzers.python_analyzer import PythonAnalyzer
from analyzers.security_analyzer import SecurityAnalyzer
from analyzers.typescript_analyzer import TypeScriptAnalyzer
from analyzers.web_analyzer import WebAnalyzer

# Registry of language analyzers
ANALYZERS = {
    "Python": PythonAnalyzer(),
    "C": CppAnalyzer(),
    "C++": CppAnalyzer(),
    "Java": JavaAnalyzer(),
    "JavaScript": JavaScriptAnalyzer(),
    "JSX": JavaScriptAnalyzer("JSX", [".jsx"]),
    "TypeScript": TypeScriptAnalyzer(),
    "TSX": TypeScriptAnalyzer(),
    "HTML": WebAnalyzer(),
    "CSS": WebAnalyzer(),
    "SCSS": WebAnalyzer(),
}

DEFAULT_ANALYZER = PythonAnalyzer()


def get_analyzer(language: str):
    """Retrieve analyzer for language or return default."""
    return ANALYZERS.get(language, DEFAULT_ANALYZER)


def analyze_static(code: str, language: str, file_path: str = "") -> List[Dict[str, Any]]:
    """
    Unified entry point for static analysis.
    Returns combined list of bugs and security findings.
    """
    if not code or not code.strip():
        return []

    analyzer = get_analyzer(language)
    bugs = analyzer.analyze_bugs(code, file_path)
    security = analyzer.analyze_security(code, file_path)

    all_findings = bugs + security
    return sorted(all_findings, key=lambda f: (f.get("line", 0), f.get("rule", "")))


def get_supported_languages() -> List[str]:
    """Returns list of supported language names."""
    return list(ANALYZERS.keys())
