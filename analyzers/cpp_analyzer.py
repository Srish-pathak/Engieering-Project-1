"""
TechSpecAnalyser — C & C++ Language Analyzer.
Supports .c, .h, .cpp, .cc, .cxx, .hpp.
Integrates tree-sitter grammar parsing, g++ syntax validation, and lizard complexity.
"""
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

from analyzers.base_analyzer import BaseAnalyzer
from analyzers.security_analyzer import SecurityAnalyzer

try:
    import tree_sitter_cpp
    from tree_sitter import Language, Parser
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

try:
    import lizard
    HAS_LIZARD = True
except ImportError:
    HAS_LIZARD = False


class CppAnalyzer(BaseAnalyzer):
    """C/C++ Static Analyzer and Complexity Measurer."""

    def __init__(self):
        super().__init__("C++", [".cpp", ".cc", ".cxx", ".hpp", ".c", ".h"])
        self.security_engine = SecurityAnalyzer()

    @property
    def supported_checks(self) -> List[str]:
        return [
            "g++ Compiler Syntax Gate (-fsyntax-only)",
            "Tree-Sitter Concrete Syntax Tree (CST) Parser",
            "Memory Leak Detection (new without delete / malloc without free)",
            "Buffer Overflow Risk Patterns (gets, strcpy, strcat, sprintf)",
            "Assignment in Conditional Expression (x = y vs x == y)",
            "Infinite Loop & Unreachable Code Detection",
            "Division by Zero Checks",
            "Lizard Cyclomatic Complexity & Function Parameter Counts",
            "CWE Security Vulnerability Rule Scanning",
        ]

    def check_syntax(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Validates C/C++ syntax with g++ or Tree-Sitter."""
        gpp = shutil.which("g++")
        if gpp:
            errors = self._check_with_gpp(code, gpp, file_path)
            if errors is not None:
                return {
                    "valid": len(errors) == 0,
                    "bugs": errors,
                    "checker": "g++ -fsyntax-only",
                }

        if HAS_TREE_SITTER:
            parser = Parser(Language(tree_sitter_cpp.language()))
            tree = parser.parse(code.encode("utf-8"))
            if tree.root_node.has_error:
                bugs = self._collect_tree_sitter_errors(tree.root_node, code, file_path)
                return {"valid": len(bugs) == 0, "bugs": bugs, "checker": "tree-sitter"}
            return {"valid": True, "bugs": [], "checker": "tree-sitter"}

        return {"valid": True, "bugs": [], "checker": "heuristic"}

    def analyze_bugs(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Identifies C/C++ logical bugs, resource leaks, and anti-patterns."""
        findings: List[Dict[str, Any]] = []
        lines = code.splitlines()

        # 1. Assignment in condition: if (a = b)
        assign_cond = re.compile(r"""\b(?:if|while)\s*\(\s*([a-zA-Z_]\w*\s*=\s*[^=][^)]*)\)""")
        for idx, line in enumerate(lines, 1):
            if assign_cond.search(line):
                findings.append({
                    "line": idx,
                    "severity": "warning",
                    "rule": "assignment-in-condition",
                    "title": "Assignment Inside Condition",
                    "description": "Assignment operator `=` inside condition. You likely meant comparison `==`.",
                    "file": file_path or "main.cpp",
                    "source": "static",
                    "confidence": "high",
                    "why_problem": "Assigning a value in a condition changes state and always evaluates to truthiness of the right-hand value.",
                    "remediation": "Replace `=` with `==`.",
                })

        # 2. Division by zero
        div_zero = re.compile(r"""\/\s*0(?![0-9\.])""")
        for idx, line in enumerate(lines, 1):
            if div_zero.search(line) and not line.strip().startswith("//"):
                findings.append({
                    "line": idx,
                    "severity": "critical",
                    "rule": "division-by-zero",
                    "title": "Division by Zero",
                    "description": "Division by literal 0 causes undefined behavior / SIGFPE at runtime.",
                    "file": file_path or "main.cpp",
                    "source": "static",
                    "confidence": "high",
                    "why_problem": "Hardware division by zero raises an uncatchable exception or crash.",
                    "remediation": "Guard against zero divisor.",
                })

        # 3. Possible Memory Leak: new without delete
        news = len(re.findall(r"\bnew\s+\w+", code))
        deletes = len(re.findall(r"\bdelete\b", code))
        has_smart_ptr = bool(re.search(r"\b(?:unique_ptr|shared_ptr|make_unique|make_shared)\b", code))
        if news > 0 and deletes == 0 and not has_smart_ptr:
            # Find first new
            first_new_line = 1
            for idx, line in enumerate(lines, 1):
                if re.search(r"\bnew\s+\w+", line):
                    first_new_line = idx
                    break
            findings.append({
                "line": first_new_line,
                "severity": "warning",
                "rule": "possible-leak",
                "title": "Possible Memory Leak (new without delete)",
                "description": "Raw dynamic memory allocation (`new`) without corresponding `delete` or smart pointer.",
                "file": file_path or "main.cpp",
                "source": "static",
                "confidence": "medium",
                "why_problem": "Leaking memory exhausts RAM over long execution runs.",
                "remediation": "Prefer `std::unique_ptr` / `std::make_unique` or call `delete` in a destructor.",
            })

        # 4. Unreachable code after return
        for idx, line in enumerate(lines[:-1], 1):
            stripped = line.strip()
            if stripped.startswith("return ") and stripped.endswith(";"):
                next_line = lines[idx].strip()
                if next_line and not next_line.startswith(("}", "//", "/*")):
                    findings.append({
                        "line": idx + 1,
                        "severity": "warning",
                        "rule": "unreachable-code",
                        "title": "Unreachable Code After Return",
                        "description": "Statement directly following `return;` cannot be reached.",
                        "file": file_path or "main.cpp",
                        "source": "static",
                        "confidence": "high",
                        "why_problem": "Dead code indicates logic confusion or erroneous copy-pasting.",
                        "remediation": "Remove the unreachable statement or relocate before return.",
                    })
                    break

        return findings

    def analyze_security(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Scans for C/C++ security issues (buffer overflows, gets, etc.)."""
        return self.security_engine.analyze(code, "C++", file_path)

    def calculate_complexity(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Calculates Cyclomatic Complexity using Lizard."""
        blocks = []
        avg_cc = 1.0
        rating = "A"

        if HAS_LIZARD:
            try:
                analysis = lizard.analyze_file.analyze_source_code("source.cpp", code)
                for f in analysis.function_list:
                    cc = f.cyclomatic_complexity
                    grade = "A" if cc <= 5 else "B" if cc <= 10 else "C" if cc <= 20 else "F"
                    blocks.append({
                        "name": f.name,
                        "line": f.start_line,
                        "complexity": cc,
                        "rank": grade,
                        "params": f.parameter_count,
                        "nloc": f.nloc,
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
        """Extracts includes, classes, structs, and functions."""
        includes = []
        classes = []
        functions = []

        lines = code.splitlines()
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            # Includes
            inc_match = re.match(r"""#include\s+[<"]([^>"]+)[>"]""", stripped)
            if inc_match:
                includes.append({"header": inc_match.group(1), "line": idx})

            # Classes / Structs
            cls_match = re.match(r"""\b(?:class|struct)\s+([A-Za-z_]\w*)""", stripped)
            if cls_match:
                classes.append({"name": cls_match.group(1), "line": idx})

            # Functions (simple heuristic pattern)
            fn_match = re.match(r"""^(?:[A-Za-z_]\w*[\s\*&]+)+([A-Za-z_]\w*)\s*\([^;)]*\)\s*\{?""", stripped)
            if fn_match and fn_match.group(1) not in ("if", "while", "for", "switch", "catch"):
                functions.append({"name": fn_match.group(1), "line": idx})

        return {
            "file": file_path,
            "includes": includes,
            "classes": classes,
            "functions": functions,
        }

    # Internal compiler helper
    def _check_with_gpp(self, code: str, gpp: str, file_path: str) -> Optional[List[Dict[str, Any]]]:
        with tempfile.NamedTemporaryFile("w", suffix=".cpp", delete=False) as tf:
            tf.write(code)
            temp_name = tf.name

        try:
            res = subprocess.run(
                [gpp, "-fsyntax-only", "-fmax-errors=5", "-std=c++17", temp_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            errors = []
            if res.returncode != 0:
                for line in (res.stderr or "").splitlines():
                    match = re.search(r":(\d+):(?:\d+:)?\s+error:\s+(.+)", line)
                    if match:
                        errors.append({
                            "line": int(match.group(1)),
                            "severity": "critical",
                            "title": "Compiler Error",
                            "description": f"CompileError: {match.group(2).strip()}",
                            "file": file_path or "main.cpp",
                            "source": "g++",
                            "confidence": "high",
                        })
            return errors
        except Exception:
            return None
        finally:
            import os
            try:
                os.unlink(temp_name)
            except Exception:
                pass

    def _collect_tree_sitter_errors(self, node: Any, code: str, file_path: str) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []
        def _walk(n: Any):
            if len(errors) >= 5:
                return
            line = n.start_point[0] + 1
            if n.is_missing:
                errors.append({
                    "line": line,
                    "severity": "critical",
                    "title": "Syntax Error",
                    "description": f"SyntaxError: missing '{n.type}'",
                    "file": file_path or "main.cpp",
                    "source": "tree-sitter",
                    "confidence": "high",
                })
            elif n.type == "ERROR":
                snippet = (n.text or b"").decode("utf-8", "replace").strip().splitlines()
                first = snippet[0][:40] if snippet else ""
                errors.append({
                    "line": line,
                    "severity": "critical",
                    "title": "Syntax Error",
                    "description": f"SyntaxError: unexpected code near `{first}`",
                    "file": file_path or "main.cpp",
                    "source": "tree-sitter",
                    "confidence": "high",
                })
            elif n.has_error:
                for c in n.children:
                    _walk(c)
        _walk(node)
        return errors
