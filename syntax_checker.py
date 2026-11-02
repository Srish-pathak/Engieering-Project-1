"""
Syntax validation for Python, C++ and Java.

How each language is checked
----------------------------
Python : the built-in compiler (`compile`) parses the code WITHOUT running it.
         This also catches mistakes such as `return` outside a function.
C++    : `g++ -fsyntax-only` if g++ is installed (real compiler errors),
         otherwise a tree-sitter grammar parse.
Java   : tree-sitter grammar parse (no JDK needed).

Every checker returns the same shape:
    {"valid": bool, "bugs": [ {line, severity, description, source} ], "checker": str}
`bugs` is ALWAYS a list (the old version returned a single dict, which crashed the UI).
"""
import os
import re
import shutil
import subprocess
import tempfile

try:
    import tree_sitter_cpp
    import tree_sitter_java
    from tree_sitter import Language, Parser

    HAS_TREE_SITTER = True
except ImportError:  # the app still works, with a simpler bracket check
    HAS_TREE_SITTER = False

MAX_REPORTED_ERRORS = 5


def _bug(line, description, source):
    return {"line": line, "severity": "critical", "description": description, "source": source}


# ---------------------------------------------------------------- Python
def _check_python(code):
    try:
        # compile() only builds bytecode; it never executes the code.
        compile(code, "<submitted code>", "exec", dont_inherit=True)
    except SyntaxError as e:  # IndentationError / TabError are subclasses
        text = (e.text or "").strip()
        message = f"{type(e).__name__}: {e.msg}"
        if text:
            message += f" (near `{text[:60]}`)"
        return [_bug(e.lineno or 1, message, "syntax")], "python compiler"
    except (ValueError, RecursionError, MemoryError) as e:
        return [_bug(1, f"Code could not be parsed: {e}", "syntax")], "python compiler"
    return [], "python compiler"


# ------------------------------------------------------------ tree-sitter
def _parser_for(language):
    grammar = tree_sitter_cpp.language() if language == "C++" else tree_sitter_java.language()
    return Parser(Language(grammar))


def _collect_ts_errors(node, errors):
    """Walk the syntax tree and record MISSING tokens and unparsable (ERROR) regions."""
    if len(errors) >= MAX_REPORTED_ERRORS:
        return
    line = node.start_point[0] + 1
    if node.is_missing:
        errors.append(_bug(line, f"SyntaxError: missing '{node.type}'", "syntax"))
    elif node.type == "ERROR":
        snippet = (node.text or b"").decode("utf-8", "replace").strip().splitlines()
        snippet = snippet[0][:40] if snippet else ""
        errors.append(_bug(line, f"SyntaxError: unexpected code near `{snippet}`", "syntax"))
    elif node.has_error:
        for child in node.children:
            _collect_ts_errors(child, errors)


def _check_tree_sitter(code, language):
    tree = _parser_for(language).parse(code.encode("utf-8"))
    errors = []
    if tree.root_node.has_error:
        _collect_ts_errors(tree.root_node, errors)
    elif language == "Java":
        # tree-sitter accepts a bare method, but javac does not.
        loose = {"method_declaration", "field_declaration", "local_variable_declaration"}
        for child in tree.root_node.children:
            if child.type in loose:
                errors.append(
                    _bug(
                        child.start_point[0] + 1,
                        "SyntaxError: Java methods and fields must be declared inside a class",
                        "syntax",
                    )
                )
    return errors, "tree-sitter"


# ------------------------------------------------------------ g++ (optional)
def _check_gpp(code):
    """Return a list of compiler errors, or None when g++ is unavailable."""
    gpp = shutil.which("g++")
    if not gpp:
        return None
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "submission.cpp")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            proc = subprocess.run(
                [gpp, "-fsyntax-only", "-std=c++17", "-fmax-errors=5", path],
                capture_output=True, text=True, timeout=15, cwd=folder,
                env={**os.environ, "LC_ALL": "C"},
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
    pattern = re.compile(r"submission\.cpp:(\d+):(?:\d+:)?\s*(?:fatal )?error:\s*(.+)")
    errors = []
    for line in proc.stderr.splitlines():
        m = pattern.search(line)
        if m:
            errors.append(_bug(int(m.group(1)), f"CompileError: {m.group(2).strip()}", "g++"))
    return errors[:MAX_REPORTED_ERRORS]


# -------------------------------------------------- fallback: bracket check
def _check_brackets(code):
    """Very small fallback used only when tree-sitter is not installed."""
    pairs = {")": "(", "]": "[", "}": "{"}
    stack, line = [], 1
    i, n = 0, len(code)
    while i < n:
        ch = code[i]
        if ch == "\n":
            line += 1
        elif code.startswith("//", i):
            while i < n and code[i] != "\n":
                i += 1
            continue
        elif code.startswith("/*", i):
            end = code.find("*/", i + 2)
            end = n if end == -1 else end + 2
            line += code.count("\n", i, end)
            i = end
            continue
        elif ch in "\"'":
            quote, i = ch, i + 1
            while i < n and code[i] != quote and code[i] != "\n":
                i += 2 if code[i] == "\\" else 1
        elif ch in "([{":
            stack.append((ch, line))
        elif ch in pairs:
            if not stack or stack[-1][0] != pairs[ch]:
                return [_bug(line, f"SyntaxError: unmatched '{ch}'", "syntax")]
            stack.pop()
        i += 1
    if stack:
        ch, opened = stack[-1]
        return [_bug(opened, f"SyntaxError: '{ch}' is never closed", "syntax")]
    return []


# ------------------------------------------------------------------ public
def check_syntax(code, language):
    if language == "Python":
        errors, checker = _check_python(code)
    elif language in ("C++", "Java"):
        errors, checker = None, ""
        if language == "C++":
            errors = _check_gpp(code)
            checker = "g++ -fsyntax-only"
        if errors is None:
            if HAS_TREE_SITTER:
                errors, checker = _check_tree_sitter(code, language)
            else:
                errors, checker = _check_brackets(code), "bracket matcher (limited)"
    else:
        errors, checker = [], "none"
    return {"valid": not errors, "bugs": errors, "checker": checker}
