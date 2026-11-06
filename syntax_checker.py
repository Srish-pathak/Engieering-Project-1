import ast
from typing import Any


def check_syntax(code: str, language: str) -> dict[str, Any]:
    """Validate Python syntax. Other languages are passed through."""
    if language != "Python":
        return {"valid": True, "bugs": []}
    try:
        ast.parse(code)
        return {"valid": True, "bugs": []}
    except SyntaxError as error:
        return {
            "valid": False,
            "bugs": [{
                "line": error.lineno,
                "severity": "critical",
                "description": "SyntaxError: {}".format(error.msg),
            }],
        }
