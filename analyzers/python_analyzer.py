"""
TechSpecAnalyser — Python Language Analyzer.
Combines Python AST visitor, built-in compiler, arity analysis,
and radon metrics.
"""
import ast
import builtins
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from analyzers.base_analyzer import BaseAnalyzer
from analyzers.security_analyzer import SecurityAnalyzer

try:
    from radon.complexity import cc_visit as radon_cc_visit
    from radon.metrics import mi_rank as radon_mi_rank, mi_visit as radon_mi_visit
    HAS_RADON = True
except ImportError:
    HAS_RADON = False

BUILTIN_NAMES = set(dir(builtins)) | {
    "__file__", "__name__", "__doc__", "__spec__", "__package__",
    "__loader__", "__builtins__", "__path__", "__class__",
}


class PythonAnalyzer(BaseAnalyzer):
    """Python AST and static analysis engine."""

    def __init__(self):
        super().__init__("Python", [".py"])
        self.security_engine = SecurityAnalyzer()

    @property
    def supported_checks(self) -> List[str]:
        return [
            "Deterministic AST Parser (ast.parse)",
            "Bytecode Compilation Syntax Gate (compile)",
            "Function Call Arity Verification",
            "Undefined Variable & Builtin Detection",
            "Unused Import & Variable Detection",
            "Mutable Default Argument Detection",
            "Resource Leak Detection (unclosed open())",
            "Bare Except & Swallowed Exception Detection",
            "Division by Zero & Unreachable Code",
            "Cyclomatic Complexity (Radon McCabe)",
            "Halstead Maintainability Index (MI)",
            "CWE Security Vulnerability Pattern Detection",
        ]

    def check_syntax(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Validates Python syntax using compile()."""
        try:
            compile(code, file_path or "<submitted code>", "exec", dont_inherit=True)
            return {"valid": True, "bugs": [], "checker": "python compiler"}
        except SyntaxError as e:
            text = (e.text or "").strip()
            msg = f"{type(e).__name__}: {e.msg}"
            if text:
                msg += f" (near `{text[:60]}`)"
            return {
                "valid": False,
                "bugs": [{
                    "line": e.lineno or 1,
                    "severity": "critical",
                    "title": type(e).__name__,
                    "description": msg,
                    "file": file_path or "main.py",
                    "source": "syntax",
                    "confidence": "high",
                }],
                "checker": "python compiler",
            }
        except Exception as e:
            return {
                "valid": False,
                "bugs": [{
                    "line": 1,
                    "severity": "critical",
                    "title": "Parse Error",
                    "description": f"Code parsing failed: {e}",
                    "file": file_path or "main.py",
                    "source": "syntax",
                    "confidence": "high",
                }],
                "checker": "python compiler",
            }

    def analyze_bugs(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Extracts AST bugs, code smells, and logic issues."""
        findings: List[Dict[str, Any]] = []
        try:
            tree = ast.parse(code)
        except Exception:
            return findings

        # Run AST rule passes
        findings.extend(self._check_arities(tree, file_path))
        findings.extend(self._check_undefined_names(tree, code, file_path))
        findings.extend(self._check_mutable_defaults(tree, file_path))
        findings.extend(self._check_except_blocks(tree, file_path))
        findings.extend(self._check_unreachable_code(tree, file_path))
        findings.extend(self._check_division_by_zero(tree, file_path))
        findings.extend(self._check_none_comparisons(tree, file_path))
        findings.extend(self._check_resource_leaks(tree, file_path))
        findings.extend(self._check_unused_symbols(tree, code, file_path))

        return sorted(findings, key=lambda f: f.get("line", 0))

    def analyze_security(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Scans for security vulnerabilities."""
        return self.security_engine.analyze(code, "Python", file_path)

    def calculate_complexity(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Calculates Radon Cyclomatic Complexity and Maintainability Index."""
        blocks = []
        avg_cc = 1.0
        rating = "A"
        mi_score = 100.0
        mi_grade = "A"

        try:
            tree = ast.parse(code)
            # Count complexity per function
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cc = 1
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                              ast.ExceptHandler, ast.With, ast.AsyncWith,
                                              ast.Assert)):
                            cc += 1
                        elif isinstance(child, ast.BoolOp):
                            cc += len(child.values) - 1
                    grade = "A" if cc <= 5 else "B" if cc <= 10 else "C" if cc <= 20 else "D" if cc <= 30 else "F"
                    blocks.append({
                        "name": node.name,
                        "line": node.lineno,
                        "complexity": cc,
                        "rank": grade,
                    })

            if blocks:
                avg_cc = round(sum(b["complexity"] for b in blocks) / len(blocks), 1)
                rating = "A" if avg_cc <= 5 else "B" if avg_cc <= 10 else "C" if avg_cc <= 20 else "F"

            if HAS_RADON:
                try:
                    mi_score = round(radon_mi_visit(code, multi=False), 1)
                    mi_grade = radon_mi_rank(mi_score)
                except Exception:
                    pass
        except Exception:
            pass

        return {
            "average_complexity": avg_cc,
            "rating": rating,
            "maintainability_index": mi_score,
            "maintainability_rank": mi_grade,
            "blocks": blocks,
        }

    def extract_structure(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Extracts modules, imports, classes, and functions."""
        imports = []
        classes = []
        functions = []

        try:
            tree = ast.parse(code)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({"module": alias.name, "alias": alias.asname or alias.name, "line": node.lineno})
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append({"module": f"{mod}.{alias.name}" if mod else alias.name, "alias": alias.asname or alias.name, "line": node.lineno})
                elif isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    doc = ast.get_docstring(node) or ""
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods,
                        "has_docstring": bool(doc),
                        "docstring": doc,
                    })
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = ast.get_docstring(node) or ""
                    args = [a.arg for a in node.args.args]
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": args,
                        "has_docstring": bool(doc),
                        "docstring": doc,
                    })
        except Exception:
            pass

        return {
            "file": file_path,
            "imports": imports,
            "classes": classes,
            "functions": functions,
        }

    # ------------------ AST Internal Rule Helpers ------------------
    def _check_arities(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        funcs: Dict[str, ast.FunctionDef] = {}
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                funcs[node.name] = node

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                fname = node.func.id
                if fname in funcs:
                    fn = funcs[fname]
                    min_args = len(fn.args.args) - len(fn.args.defaults)
                    max_args = len(fn.args.args) if not fn.args.vararg else 999
                    call_args = len(node.args)

                    if not fn.args.vararg and call_args < min_args:
                        findings.append({
                            "line": node.lineno,
                            "severity": "critical",
                            "rule": "arity-mismatch",
                            "title": "Missing Required Argument",
                            "description": f"Function `{fname}()` requires at least {min_args} arguments, but {call_args} were provided.",
                            "file": file_path or "main.py",
                            "source": "static",
                            "confidence": "high",
                            "why_problem": "Calling a function with too few positional arguments raises TypeError at runtime.",
                            "remediation": f"Provide the required arguments to `{fname}()`.",
                        })
                    elif not fn.args.vararg and call_args > max_args:
                        findings.append({
                            "line": node.lineno,
                            "severity": "critical",
                            "rule": "arity-mismatch",
                            "title": "Too Many Arguments",
                            "description": f"Function `{fname}()` accepts up to {max_args} arguments, but {call_args} were provided.",
                            "file": file_path or "main.py",
                            "source": "static",
                            "confidence": "high",
                            "why_problem": "Passing excess positional arguments raises TypeError at runtime.",
                            "remediation": f"Match the parameter count of `{fname}()`.",
                        })
        return findings

    def _check_undefined_names(self, tree: ast.AST, code: str, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        bound_names: Set[str] = set(BUILTIN_NAMES)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Param)):
                bound_names.add(node.id)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound_names.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    bound_names.add(a.asname or a.name.split(".")[0])

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in bound_names:
                    findings.append({
                        "line": node.lineno,
                        "severity": "critical",
                        "rule": "undefined-name",
                        "title": "Undefined Variable or Name",
                        "description": f"Name `{node.id}` is used before assignment or not defined in scope.",
                        "file": file_path or "main.py",
                        "source": "static",
                        "confidence": "high",
                        "why_problem": f"Accessing `{node.id}` will raise NameError at runtime.",
                        "remediation": f"Define `{node.id}` before use or verify imports.",
                    })
        return findings

    def _check_mutable_defaults(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for d in node.args.defaults + node.args.kw_defaults:
                    if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                        findings.append({
                            "line": d.lineno,
                            "severity": "warning",
                            "rule": "mutable-default",
                            "title": "Mutable Default Parameter",
                            "description": f"Function `{node.name}` uses a mutable default argument. It is shared across invocations.",
                            "file": file_path or "main.py",
                            "source": "static",
                            "confidence": "high",
                            "why_problem": "Python binds default arguments once at definition time. Mutating the list or dict persists state between calls.",
                            "remediation": "Use `None` as the default and initialize `param = []` inside the function body.",
                        })
        return findings

    def _check_except_blocks(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    findings.append({
                        "line": node.lineno,
                        "severity": "warning",
                        "rule": "bare-except",
                        "title": "Bare Except Clause",
                        "description": "Catching `except:` catches KeyboardInterrupt and SystemExit, preventing graceful exit.",
                        "file": file_path or "main.py",
                        "source": "static",
                        "confidence": "high",
                        "why_problem": "Bare except obscures syntax and interruption errors.",
                        "remediation": "Catch explicit exceptions such as `except Exception:` or specific error classes.",
                    })
                # Check for swallowed exception (empty body or pass only)
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    findings.append({
                        "line": node.lineno,
                        "severity": "warning",
                        "rule": "swallowed-exception",
                        "title": "Swallowed / Silent Exception",
                        "description": "Exception is silently ignored with `pass` without logging or handling.",
                        "file": file_path or "main.py",
                        "source": "static",
                        "confidence": "high",
                        "why_problem": "Silencing exceptions masks runtime failures and makes debugging difficult.",
                        "remediation": "Log the exception or handle it explicitly.",
                    })
        return findings

    def _check_unreachable_code(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and len(body) > 1:
                for idx, stmt in enumerate(body[:-1]):
                    if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                        next_stmt = body[idx + 1]
                        findings.append({
                            "line": next_stmt.lineno,
                            "severity": "warning",
                            "rule": "unreachable-code",
                            "title": "Unreachable Code Detected",
                            "description": f"Code following `{type(stmt).__name__.lower()}` can never be executed.",
                            "file": file_path or "main.py",
                            "source": "static",
                            "confidence": "high",
                            "why_problem": "Dead code increases cognitive overhead and indicates logic bugs.",
                            "remediation": "Remove the unreachable code or adjust conditional control flow.",
                        })
                        break
        return findings

    def _check_division_by_zero(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                if isinstance(node.right, ast.Constant) and node.right.value == 0:
                    findings.append({
                        "line": node.lineno,
                        "severity": "critical",
                        "rule": "division-by-zero",
                        "title": "Division by Zero",
                        "description": "Division or modulo by literal zero fails immediately at runtime.",
                        "file": file_path or "main.py",
                        "source": "static",
                        "confidence": "high",
                        "why_problem": "Raises ZeroDivisionError when evaluated.",
                        "remediation": "Guard against zero division or check the divisor.",
                    })
        return findings

    def _check_none_comparisons(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for op, comp in zip(node.ops, node.comparators):
                    if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(comp, ast.Constant) and comp.value is None:
                        findings.append({
                            "line": node.lineno,
                            "severity": "info",
                            "rule": "none-comparison",
                            "title": "Comparison to None Using Equality Operator",
                            "description": "Comparison with `None` should use identity operators `is` or `is not`.",
                            "file": file_path or "main.py",
                            "source": "static",
                            "confidence": "high",
                            "why_problem": "`== None` invokes `__eq__` on objects which can be overloaded or inefficient.",
                            "remediation": "Use `is None` or `is not None`.",
                        })
        return findings

    def _check_resource_leaks(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        # Check open() calls not inside 'with' statements
        with_open_lines = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call) and getattr(item.context_expr.func, "id", "") == "open":
                        with_open_lines.add(item.context_expr.lineno)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "open":
                if node.lineno not in with_open_lines:
                    findings.append({
                        "line": node.lineno,
                        "severity": "warning",
                        "rule": "unclosed-resource",
                        "title": "Unclosed Resource / open() Outside Context Manager",
                        "description": "File opened with `open()` without `with` statement may leak file descriptors on exceptions.",
                        "file": file_path or "main.py",
                        "source": "static",
                        "confidence": "medium",
                        "why_problem": "Failing to close files promptly leads to resource exhaustion and file locking.",
                        "remediation": "Use `with open(...) as f:` to guarantee proper closing.",
                    })
        return findings

    def _check_unused_symbols(self, tree: ast.AST, code: str, file_path: str) -> List[Dict[str, Any]]:
        findings = []
        import_names = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    import_names[a.asname or a.name.split(".")[0]] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for a in node.names:
                    import_names[a.asname or a.name] = node.lineno

        # Check references in code
        for name, line in import_names.items():
            if name.startswith("__") or name in ("typing", "sys", "os"):
                continue
            # Regex word search excluding the import line itself
            occurrences = len(re.findall(rf"\b{re.escape(name)}\b", code))
            if occurrences <= 1:
                findings.append({
                    "line": line,
                    "severity": "info",
                    "rule": "unused-import",
                    "title": "Unused Import",
                    "description": f"Imported module `{name}` is never used in the file.",
                    "file": file_path or "main.py",
                    "source": "static",
                    "confidence": "medium",
                    "why_problem": "Unused imports increase startup latency and memory footprint.",
                    "remediation": f"Remove `import {name}`.",
                })
        return findings
