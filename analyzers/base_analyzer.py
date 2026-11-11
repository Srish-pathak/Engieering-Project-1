"""
TechSpecAnalyser — Base Language Analyzer Interface.
Defines standard contracts for language adapters.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseAnalyzer(ABC):
    """Abstract base class for all language analyzers."""

    def __init__(self, language: str, extensions: List[str]):
        self.language = language
        self.extensions = extensions

    @property
    @abstractmethod
    def supported_checks(self) -> List[str]:
        """List of supported analysis capabilities for this language."""
        pass

    @abstractmethod
    def check_syntax(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """
        Validates language syntax.
        Returns: {"valid": bool, "bugs": List[Dict], "checker": str}
        """
        pass

    @abstractmethod
    def analyze_bugs(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """
        Runs deterministic static analysis to find bugs and code smells.
        Returns list of finding dicts.
        """
        pass

    @abstractmethod
    def analyze_security(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """
        Finds security vulnerabilities and insecure coding patterns.
        Returns list of finding dicts with CWE annotations.
        """
        pass

    @abstractmethod
    def calculate_complexity(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """
        Calculates cyclomatic complexity, maintainability, and code metrics.
        """
        pass

    @abstractmethod
    def extract_structure(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """
        Extracts structural symbols: imports, classes, functions, entry points.
        """
        pass

    def run_all(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Convenience method running all analysis passes."""
        syntax = self.check_syntax(code, file_path)
        if not syntax["valid"]:
            return {
                "language": self.language,
                "file_path": file_path,
                "syntax": syntax,
                "bugs": syntax["bugs"],
                "security": [],
                "complexity": {"average_complexity": 0, "rating": "N/A", "blocks": []},
                "structure": {"imports": [], "classes": [], "functions": []},
            }

        bugs = self.analyze_bugs(code, file_path)
        security = self.analyze_security(code, file_path)
        complexity = self.calculate_complexity(code, file_path)
        structure = self.extract_structure(code, file_path)

        return {
            "language": self.language,
            "file_path": file_path,
            "syntax": syntax,
            "bugs": bugs,
            "security": security,
            "complexity": complexity,
            "structure": structure,
            "supported_checks": self.supported_checks,
        }
