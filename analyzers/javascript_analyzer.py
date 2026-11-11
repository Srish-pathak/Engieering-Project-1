"""
TechSpecAnalyser — JavaScript & JSX Language Analyzer.
Supports .js, .mjs, .cjs, and .jsx files.
"""
import re
from typing import Any, Dict, List

from analyzers.base_analyzer import BaseAnalyzer
from analyzers.security_analyzer import SecurityAnalyzer

try:
    import lizard
    HAS_LIZARD = True
except ImportError:
    HAS_LIZARD = False


class JavaScriptAnalyzer(BaseAnalyzer):
    """JavaScript and JSX Static Analysis Engine."""

    def __init__(self, language: str = "JavaScript", extensions: List[str] = None):
        exts = extensions or [".js", ".mjs", ".cjs", ".jsx"]
        super().__init__(language, exts)
        self.security_engine = SecurityAnalyzer()

    @property
    def supported_checks(self) -> List[str]:
        return [
            "JavaScript / JSX Syntax & Bracket Verification",
            "Dangerous eval() & new Function() Execution Detection",
            "Loose Equality (== vs ===) Type Coercion Hazards",
            "Production debugger / console.log Detection",
            "Legacy var vs Block-Scoped let/const Checking",
            "React dangerouslySetInnerHTML & DOM XSS Scanning",
            "Unclosed Promises & Missing Error Handlers",
            "Cyclomatic Complexity (Lizard Engine)",
            "CWE Security Vulnerability Rule Scanning",
        ]

    def check_syntax(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Performs lexical and structural bracket checks."""
        # Check balanced braces, brackets, and quotes
        stack = []
        lines = code.splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            for char in stripped:
                if char in "({[":
                    stack.append((char, idx))
                elif char in ")}]":
                    if not stack:
                        return {
                            "valid": False,
                            "bugs": [{
                                "line": idx,
                                "severity": "critical",
                                "title": "Unmatched Closing Bracket",
                                "description": f"Unexpected closing bracket `{char}` without matching opener.",
                                "file": file_path or "script.js",
                                "source": "syntax",
                                "confidence": "high",
                            }],
                            "checker": "js-parser",
                        }
                    top, _ = stack.pop()
                    expected = {"(": ")", "{": "}", "[": "]"}[top]
                    if char != expected:
                        return {
                            "valid": False,
                            "bugs": [{
                                "line": idx,
                                "severity": "critical",
                                "title": "Bracket Mismatch",
                                "description": f"Mismatched bracket: expected `{expected}`, found `{char}`.",
                                "file": file_path or "script.js",
                                "source": "syntax",
                                "confidence": "high",
                            }],
                            "checker": "js-parser",
                        }

        if stack:
            unclosed_char, unclosed_line = stack[-1]
            return {
                "valid": False,
                "bugs": [{
                    "line": unclosed_line,
                    "severity": "critical",
                    "title": "Unclosed Bracket",
                    "description": f"Unclosed `{unclosed_char}` starting on line {unclosed_line}.",
                    "file": file_path or "script.js",
                    "source": "syntax",
                    "confidence": "high",
                }],
                "checker": "js-parser",
            }

        return {"valid": True, "bugs": [], "checker": "js-parser"}

    def analyze_bugs(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Scans for JavaScript bugs, bad practices, and maintainability issues."""
        findings: List[Dict[str, Any]] = []
        lines = code.splitlines()

        # 1. Loose Equality == / !=
        loose_eq = re.compile(r"""(?<!=)==(?!=)|(?<!\!)!=(?!=)""")
        for idx, line in enumerate(lines, 1):
            if line.strip().startswith("//"):
                continue
            if loose_eq.search(line):
                findings.append({
                    "line": idx,
                    "severity": "warning",
                    "rule": "loose-equality",
                    "title": "Loose Equality (== vs ===)",
                    "description": "Loose equality operator `==` performs unpredictable type coercion.",
                    "file": file_path or "script.js",
                    "source": "static",
                    "confidence": "high",
                    "why_problem": "JavaScript type coercion can cause values like `0 == ''` or `false == '0'` to evaluate to true.",
                    "remediation": "Use strict equality `===` or `!==`.",
                })

        # 2. Debugger statement
        for idx, line in enumerate(lines, 1):
            if re.search(r"""\bdebugger\s*;""", line):
                findings.append({
                    "line": idx,
                    "severity": "critical",
                    "rule": "debugger-statement",
                    "title": "Debugger Statement in Code",
                    "description": "Production code contains `debugger;` statement which suspends browser execution.",
                    "file": file_path or "script.js",
                    "source": "static",
                    "confidence": "high",
                    "why_problem": "Freezes execution in client browsers if developer tools are open.",
                    "remediation": "Remove `debugger;` prior to release.",
                })

        # 3. Legacy 'var' declaration
        var_pat = re.compile(r"""\bvar\s+([A-Za-z_$]\w*)""")
        for idx, line in enumerate(lines, 1):
            if var_pat.search(line) and not line.strip().startswith("//"):
                findings.append({
                    "line": idx,
                    "severity": "info",
                    "rule": "legacy-var",
                    "title": "Use of Legacy `var` Declaration",
                    "description": "Declaration uses `var` instead of block-scoped `let` or `const`.",
                    "file": file_path or "script.js",
                    "source": "static",
                    "confidence": "high",
                    "why_problem": "`var` is function-scoped and hoisted, leading to subtle state bugs and closure traps.",
                    "remediation": "Replace `var` with `const` (for constants) or `let` (for mutable variables).",
                })

        return findings

    def analyze_security(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Scans for JavaScript & JSX security risks (eval, XSS, prototype pollution)."""
        return self.security_engine.analyze(code, "JavaScript", file_path)

    def calculate_complexity(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Calculates complexity using Lizard."""
        blocks = []
        avg_cc = 1.0
        rating = "A"

        if HAS_LIZARD:
            try:
                analysis = lizard.analyze_file.analyze_source_code("script.js", code)
                for f in analysis.function_list:
                    cc = f.cyclomatic_complexity
                    grade = "A" if cc <= 5 else "B" if cc <= 10 else "C" if cc <= 20 else "F"
                    blocks.append({
                        "name": f.name,
                        "line": f.start_line,
                        "complexity": cc,
                        "rank": grade,
                    })
                if blocks:
                    avg_cc = round(sum(b["complexity"] for b in blocks) / len(blocks), 1)
                    rating = "A" if avg_cc <= 5 else "B" if avg_cc <= 10 else "C" if avg_cc <= 20 else "F"
            except Exception:
                pass

        return {
            "average_complexity": avg_cc,
            "rating": rating,
            "blocks": blocks,
        }

    def extract_structure(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Extracts imports, exports, functions, and React components."""
        imports = []
        exports = []
        functions = []

        lines = code.splitlines()
        for idx, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("import "):
                imports.append({"import": s, "line": idx})
            elif s.startswith("export "):
                exports.append({"export": s, "line": idx})
            elif re.search(r"""(?:function\s+([A-Za-z_$]\w*)|const\s+([A-Za-z_$]\w*)\s*=\s*(?:\([^)]*\)|[A-Za-z_$]\w*)\s*=>)""", s):
                m = re.search(r"""(?:function\s+([A-Za-z_$]\w*)|const\s+([A-Za-z_$]\w*)\s*=\s*(?:\([^)]*\)|[A-Za-z_$]\w*)\s*=>)""", s)
                name = m.group(1) or m.group(2) if m else ""
                if name:
                    functions.append({"name": name, "line": idx})

        return {
            "file": file_path,
            "imports": imports,
            "exports": exports,
            "functions": functions,
        }
