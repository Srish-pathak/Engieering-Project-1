import ast
from typing import Any


class StaticAnalyzer(ast.NodeVisitor):
    """Find calls whose arguments do not match the function definition."""

    def __init__(self) -> None:
        self.signatures: dict[str, dict[str, Any]] = {}
        self.bugs: list[dict[str, Any]] = []
        self.collecting = True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self.collecting:
            positional = [a.arg for a in node.args.posonlyargs] + [a.arg for a in node.args.args]
            required_count = len(positional) - len(node.args.defaults)
            self.signatures[node.name] = {
                "positional": positional,
                "required": set(positional[:required_count]),
                "posonly": len(node.args.posonlyargs),
                "keywords": set(positional[len(node.args.posonlyargs):]) | {a.arg for a in node.args.kwonlyargs},
                "kw_required": {a.arg for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if d is None},
                "vararg": node.args.vararg is not None,
                "kwarg": node.args.kwarg is not None,
            }
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        if not self.collecting and isinstance(node.func, ast.Name) and node.func.id in self.signatures:
            problem = self._mismatch(node, node.func.id)
            if problem:
                self.bugs.append({"line": node.lineno, "severity": "critical", "description": problem})
        self.generic_visit(node)

    def _mismatch(self, node: ast.Call, name: str) -> str | None:
        sig = self.signatures[name]
        if any(isinstance(a, ast.Starred) for a in node.args) or any(k.arg is None for k in node.keywords):
            return None  # unknown number of values

        supplied: set[str] = set()
        for index, _ in enumerate(node.args):
            if index >= len(sig["positional"]):
                if not sig["vararg"]:
                    return "Function '{}' received too many positional arguments.".format(name)
                continue
            supplied.add(sig["positional"][index])

        for keyword in node.keywords:
            if keyword.arg in sig["positional"][:sig["posonly"]]:
                return "Function '{}' does not accept '{}' as a keyword argument.".format(name, keyword.arg)
            if keyword.arg not in sig["keywords"]:
                if not sig["kwarg"]:
                    return "Function '{}' received unexpected keyword argument '{}'.".format(name, keyword.arg)
                continue
            if keyword.arg in supplied:
                return "Function '{}' received multiple values for argument '{}'.".format(name, keyword.arg)
            supplied.add(keyword.arg)

        missing = (sig["required"] | sig["kw_required"]) - supplied
        if missing:
            return "Function '{}' is missing required argument(s): {}.".format(name, ", ".join(sorted(missing)))
        return None


def analyze_static(code: str, language: str) -> list[dict[str, Any]]:
    """Return call-signature findings for Python code."""
    if language != "Python":
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    analyzer = StaticAnalyzer()
    analyzer.visit(tree)          # pass 1: collect every function signature
    analyzer.collecting = False
    analyzer.visit(tree)          # pass 2: check every call
    return analyzer.bugs
