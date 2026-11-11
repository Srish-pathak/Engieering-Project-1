"""
TechSpecAnalyser — TypeScript & TSX Language Analyzer.
Supports .ts and .tsx files.
Extends JavaScript analysis with TypeScript-specific type-safety rules.
"""
import re
from typing import Any, Dict, List

from analyzers.javascript_analyzer import JavaScriptAnalyzer


class TypeScriptAnalyzer(JavaScriptAnalyzer):
    """TypeScript & TSX Static Analyzer."""

    def __init__(self):
        super().__init__("TypeScript", [".ts", ".tsx"])

    @property
    def supported_checks(self) -> List[str]:
        return super().supported_checks + [
            "TypeScript Type Safety & Suppressed Check Detection (@ts-ignore)",
            "Excessive / Unsafe `any` Type Usage Detection",
            "Non-Null Assertion Operator (!) Risk Detection",
            "Interface & Type Alias Structural Extraction",
        ]

    def analyze_bugs(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Runs JavaScript bug analysis plus TypeScript type safety checks."""
        findings = super().analyze_bugs(code, file_path)
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()

            # 1. @ts-ignore or @ts-nocheck
            if re.search(r"""//\s*@ts-(?:ignore|nocheck)\b""", stripped):
                findings.append({
                    "line": idx,
                    "severity": "warning",
                    "rule": "suppressed-type-check",
                    "title": "Suppressed TypeScript Type Checking",
                    "description": "Directive suppresses type errors, defeating TypeScript compiler guarantees.",
                    "file": file_path or "index.ts",
                    "source": "static",
                    "confidence": "high",
                    "why_problem": "Hiding compiler errors leads to runtime crashes in production.",
                    "remediation": "Resolve the underlying type mismatch rather than suppressing it.",
                })

            # 2. Unsafe 'any' type usage
            if re.search(r"""(?::\s*any\b|\bas\s+any\b)""", stripped) and not stripped.startswith("//"):
                findings.append({
                    "line": idx,
                    "severity": "info",
                    "rule": "unsafe-any-type",
                    "title": "Unsafe `any` Type Annotation",
                    "description": "Usage of `any` disables static type safety checks for this symbol.",
                    "file": file_path or "index.ts",
                    "source": "static",
                    "confidence": "medium",
                    "why_problem": "`any` propagates unverified assumptions throughout the codebase.",
                    "remediation": "Provide explicit types or use `unknown` with runtime narrowing.",
                })

            # 3. Non-null assertion operator !.
            if re.search(r"""[a-zA-Z0-9_]\s*!\.\s*[a-zA-Z0-9_]""", stripped) and not stripped.startswith("//"):
                findings.append({
                    "line": idx,
                    "severity": "info",
                    "rule": "non-null-assertion",
                    "title": "Non-Null Assertion Operator (!.) Risk",
                    "description": "Bypassing null-checking with `!` may cause TypeError at runtime.",
                    "file": file_path or "index.ts",
                    "source": "static",
                    "confidence": "medium",
                    "why_problem": "If the operand is null/undefined, a TypeError crash occurs when accessed.",
                    "remediation": "Use optional chaining `?.` or explicit null guards.",
                })

        return sorted(findings, key=lambda f: f.get("line", 0))

    def extract_structure(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Extracts interfaces, types, functions, and components."""
        structure = super().extract_structure(code, file_path)
        types = []
        interfaces = []

        lines = code.splitlines()
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            # Interfaces
            m_iface = re.match(r"""(?:export\s+)?interface\s+([A-Za-z0-9_]+)""", s)
            if m_iface:
                interfaces.append({"name": m_iface.group(1), "line": idx})
            # Types
            m_type = re.match(r"""(?:export\s+)?type\s+([A-Za-z0-9_]+)\s*=""", s)
            if m_type:
                types.append({"name": m_type.group(1), "line": idx})

        structure["interfaces"] = interfaces
        structure["types"] = types
        return structure
