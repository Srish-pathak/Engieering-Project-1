"""
Static analysis: finds likely mistakes WITHOUT running the code.

Python  : walks the AST (Abstract Syntax Tree) built by Python's `ast` module.
C++/Java: walks the tree-sitter syntax tree.

Design rule: it is better to MISS a bug than to report a bug that is not there,
so every rule is deliberately conservative (no false alarms in a live demo).

Every finding looks like:
    {"line": int, "severity": "critical|warning|info", "description": str,
     "source": "static", "rule": short-rule-id}
"""
import ast
import builtins
import re

try:
    import tree_sitter_cpp
    import tree_sitter_java
    from tree_sitter import Language, Parser

    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False

BUILTIN_NAMES = set(dir(builtins)) | {
    "__file__", "__name__", "__doc__", "__spec__", "__package__",
    "__loader__", "__builtins__", "__path__", "__class__",
}
SHADOWABLE = {
    "list", "dict", "set", "str", "int", "float", "sum", "max", "min", "len",
    "input", "type", "id", "map", "filter", "sorted", "all", "any", "next",
    "iter", "object", "format", "range", "tuple", "bool", "abs", "round",
}


def _finding(line, severity, description, rule):
    return {
        "line": line, "severity": severity, "description": description,
        "source": "static", "rule": rule,
    }


# =====================================================================
#                              PYTHON
# =====================================================================
def _all_args(args):
    """Every parameter of a function signature, as ast.arg objects."""
    found = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
    if args.vararg:
        found.append(args.vararg)
    if args.kwarg:
        found.append(args.kwarg)
    return found


def _bound_names(tree):
    """
    Names that get a value somewhere in the file.
    Returns (names_bound_by_anything_except_def, names_bound_by_def).
    """
    other, funcs = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.add(n.name)
            other.update(a.arg for a in _all_args(n.args))
        elif isinstance(n, ast.Lambda):
            other.update(a.arg for a in _all_args(n.args))
        elif isinstance(n, ast.ClassDef):
            other.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            other.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for alias in n.names:
                other.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            other.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            other.update(n.names)
        elif type(n).__name__ in ("MatchAs", "MatchStar") and getattr(n, "name", None):
            other.add(n.name)
        elif type(n).__name__ == "MatchMapping" and getattr(n, "rest", None):
            other.add(n.rest)
        elif type(n).__name__ in ("TypeVar", "ParamSpec", "TypeVarTuple"):
            other.add(n.name)
    return other, funcs


def _plain_functions(tree):
    """name -> [FunctionDef, ...] for functions that are NOT methods of a class."""
    defs = {}

    def visit(node, in_class):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not in_class:
                    defs.setdefault(child.name, []).append(child)
                visit(child, False)
            elif isinstance(child, ast.ClassDef):
                visit(child, True)
            else:
                visit(child, in_class)

    visit(tree, False)
    return defs


def _check_calls(tree):
    """
    Accurate argument checking. Understands default values, *args, **kwargs,
    keyword arguments, keyword-only and positional-only parameters.
    Skips anything it cannot be sure about (decorated or redefined functions).
    """
    findings = []
    other_bound, _ = _bound_names(tree)
    candidates = {}
    for name, defs in _plain_functions(tree).items():
        if len(defs) == 1 and not defs[0].decorator_list and name not in other_bound:
            candidates[name] = defs[0]

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        func = candidates.get(node.func.id)
        if func is None:
            continue
        # f(*items) or f(**options): the real argument count is unknown, so skip.
        if any(isinstance(a, ast.Starred) for a in node.args) or any(
            k.arg is None for k in node.keywords
        ):
            continue

        a = func.args
        positional = [p.arg for p in a.posonlyargs + a.args]
        pos_only = {p.arg for p in a.posonlyargs}
        kw_only = [p.arg for p in a.kwonlyargs]
        n_defaults = len(a.defaults)
        required = positional[: len(positional) - n_defaults] if n_defaults else list(positional)
        required += [p.arg for p, d in zip(a.kwonlyargs, a.kw_defaults) if d is None]

        problems = []
        given_pos = len(node.args)
        if given_pos > len(positional) and not a.vararg:
            problems.append(
                f"takes at most {len(positional)} positional argument(s) but {given_pos} were given"
            )
        supplied = set(positional[:given_pos])
        for kw in node.keywords:
            if kw.arg in supplied:
                problems.append(f"got multiple values for argument '{kw.arg}'")
            elif kw.arg in pos_only or (
                kw.arg not in positional and kw.arg not in kw_only and not a.kwarg
            ):
                problems.append(f"got an unexpected keyword argument '{kw.arg}'")
            supplied.add(kw.arg)
        missing = [r for r in required if r not in supplied]
        if missing and not problems:
            problems.append("missing required argument(s): " + ", ".join(missing))

        if problems:
            sig = ", ".join(positional + kw_only)
            findings.append(
                _finding(
                    node.lineno, "critical",
                    f"Call to `{func.name}({sig})` is wrong: {problems[0]}.",
                    "bad-call",
                )
            )
    return findings


def _check_undefined_names(tree):
    other, funcs = _bound_names(tree)
    defined = other | funcs | BUILTIN_NAMES
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and any(a.name == "*" for a in n.names):
            return []  # star-import: we cannot know the names, so stay silent
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in (
            "exec", "globals", "locals", "vars", "setattr",
        ):
            return []
    findings, seen = [], set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            if n.id not in defined and n.id not in seen:
                seen.add(n.id)
                findings.append(
                    _finding(n.lineno, "critical",
                             f"Name `{n.id}` is not defined (NameError at runtime). Check for a typo.",
                             "undefined-name")
                )
    return findings


def _check_unused_imports(tree):
    imported = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for alias in n.names:
                imported.setdefault(alias.asname or alias.name.split(".")[0], n.lineno)
        elif isinstance(n, ast.ImportFrom) and n.module != "__future__":
            for alias in n.names:
                if alias.name != "*":
                    imported.setdefault(alias.asname or alias.name, n.lineno)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    for n in ast.walk(tree):  # names exported through __all__ count as used
        if isinstance(n, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets
        ):
            used.update(
                c.value for c in ast.walk(n.value)
                if isinstance(c, ast.Constant) and isinstance(c.value, str)
            )
    return [
        _finding(line, "info", f"Import `{name}` is never used.", "unused-import")
        for name, line in imported.items() if name not in used
    ]


def _walk_own_scope(func):
    """Yield nodes of a function, but do not enter nested functions/classes."""
    stack = list(func.body)
    while stack:
        node = stack.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
                stack.append(child)


def _check_unused_variables(tree):
    findings = []
    for func in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        loads = {n.id for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        declared = set()
        dynamic = False
        for n in ast.walk(func):
            if isinstance(n, (ast.Global, ast.Nonlocal)):
                declared.update(n.names)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in (
                "locals", "vars", "exec", "eval",
            ):
                dynamic = True
        if dynamic:
            continue
        assigned = {}
        for n in _walk_own_scope(func):
            targets = []
            if isinstance(n, ast.Assign):
                targets = [t for t in n.targets if isinstance(t, ast.Name)]
            elif isinstance(n, ast.AnnAssign) and n.value is not None and isinstance(n.target, ast.Name):
                targets = [n.target]
            elif isinstance(n, ast.NamedExpr):
                targets = [n.target]
            elif isinstance(n, ast.withitem) and isinstance(n.optional_vars, ast.Name):
                targets = [n.optional_vars]
            for t in targets:
                assigned.setdefault(t.id, t.lineno)
        for name, line in sorted(assigned.items(), key=lambda kv: kv[1]):
            if name not in loads and name not in declared and not name.startswith("_"):
                findings.append(
                    _finding(line, "info", f"Variable `{name}` is assigned but never used.", "unused-variable")
                )
    return findings


def _check_mutable_defaults(tree):
    findings = []
    for func in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        for default in list(func.args.defaults) + [d for d in func.args.kw_defaults if d is not None]:
            is_mutable = isinstance(default, (ast.List, ast.Dict, ast.Set)) or (
                isinstance(default, ast.Call) and isinstance(default.func, ast.Name)
                and default.func.id in ("list", "dict", "set")
            )
            if is_mutable:
                findings.append(
                    _finding(default.lineno, "warning",
                             f"Mutable default argument in `{func.name}`: the same object is shared "
                             "between calls. Use `None` and create the object inside the function.",
                             "mutable-default")
                )
    return findings


def _check_exceptions(tree):
    findings = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.ExceptHandler):
            continue
        only_pass = all(
            isinstance(s, ast.Pass) or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))
            for s in n.body
        )
        if n.type is None:
            findings.append(
                _finding(n.lineno, "warning",
                         "Bare `except:` also catches KeyboardInterrupt and hides real errors. "
                         "Catch a specific exception instead.", "bare-except")
            )
        elif only_pass:
            findings.append(
                _finding(n.lineno, "warning",
                         "The exception is caught and silently ignored. At least log it.",
                         "swallowed-exception")
            )
    return findings


def _check_comparisons(tree):
    findings = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Compare):
            continue
        for op, right in zip(n.ops, n.comparators):
            if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(right, ast.Constant) and right.value is None:
                findings.append(
                    _finding(n.lineno, "info",
                             "Compare with None using `is None` / `is not None`, not `==` / `!=`.",
                             "none-comparison")
                )
            if (
                isinstance(op, (ast.Is, ast.IsNot)) and isinstance(right, ast.Constant)
                and isinstance(right.value, (str, bytes, int, float)) and not isinstance(right.value, bool)
            ):
                findings.append(
                    _finding(n.lineno, "warning",
                             "`is` compares object identity, not value. Use `==` to compare with a literal.",
                             "is-literal")
                )
    return findings


def _check_division_by_zero(tree):
    findings = []
    for n in ast.walk(tree):
        if (
            isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Div, ast.FloorDiv, ast.Mod))
            and isinstance(n.right, ast.Constant) and not isinstance(n.right.value, bool)
            and isinstance(n.right.value, (int, float)) and n.right.value == 0
        ):
            findings.append(
                _finding(n.lineno, "critical", "Division by zero: this raises ZeroDivisionError.", "division-by-zero")
            )
    return findings


def _check_unreachable(tree):
    findings = []
    for n in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            stmts = getattr(n, field, None)
            if not isinstance(stmts, list):
                continue
            for i, stmt in enumerate(stmts[:-1]):
                if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                    findings.append(
                        _finding(stmts[i + 1].lineno, "warning",
                                 f"Unreachable code: it comes after `{type(stmt).__name__.lower()}` "
                                 "and can never run.", "unreachable-code")
                    )
                    break
    return findings


def _check_infinite_loops(tree):
    findings = []
    exits = (ast.Break, ast.Return, ast.Raise, ast.Yield, ast.YieldFrom)
    for n in ast.walk(tree):
        if isinstance(n, ast.While) and isinstance(n.test, ast.Constant) and n.test.value:
            leaves = False
            for child in ast.walk(n):
                if isinstance(child, exits):
                    leaves = True
                elif isinstance(child, ast.Call):
                    name = getattr(child.func, "id", None) or getattr(child.func, "attr", None)
                    if name in ("exit", "quit", "_exit"):
                        leaves = True
            if not leaves:
                findings.append(
                    _finding(n.lineno, "warning",
                             "`while True` has no break, return or raise, so it may never stop.",
                             "infinite-loop")
                )
    return findings


def _check_dangerous_calls(tree):
    findings = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("eval", "exec"):
            findings.append(
                _finding(n.lineno, "warning",
                         f"`{n.func.id}()` runs arbitrary code. Avoid it with untrusted input.",
                         "dangerous-call")
            )
    return findings


def _check_shadowed_builtins(tree):
    findings, seen = [], set()
    for n in ast.walk(tree):
        names = []
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            names = [(n.id, n.lineno)]
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names = [(n.name, n.lineno)] + [(a.arg, n.lineno) for a in _all_args(n.args)]
        for name, line in names:
            if name in SHADOWABLE and name not in seen:
                seen.add(name)
                findings.append(
                    _finding(line, "info",
                             f"`{name}` hides Python's built-in `{name}`. Pick a different name.",
                             "shadowed-builtin")
                )
    return findings


def _check_redefinitions(tree):
    findings = []
    for n in ast.walk(tree):
        body = getattr(n, "body", None)
        if not isinstance(body, list) or not isinstance(n, (ast.Module, ast.ClassDef)):
            continue
        seen = {}
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and not stmt.decorator_list:
                if stmt.name in seen:
                    findings.append(
                        _finding(stmt.lineno, "warning",
                                 f"Function `{stmt.name}` is defined again (first defined on line "
                                 f"{seen[stmt.name]}). The earlier version is overwritten.",
                                 "redefined-function")
                    )
                seen[stmt.name] = stmt.lineno
    return findings


PYTHON_RULES = [
    _check_calls, _check_undefined_names, _check_unused_imports, _check_unused_variables,
    _check_mutable_defaults, _check_exceptions, _check_comparisons, _check_division_by_zero,
    _check_unreachable, _check_infinite_loops, _check_dangerous_calls,
    _check_shadowed_builtins, _check_redefinitions,
]


def _analyze_python(code):
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []  # syntax errors are reported by syntax_checker.py
    findings = []
    for rule in PYTHON_RULES:
        findings.extend(rule(tree))
    return findings


# =====================================================================
#                         C++  and  JAVA
# =====================================================================
_PARSERS = {}


def _parser_for(language):
    if language not in _PARSERS:
        grammar = tree_sitter_cpp.language() if language == "C++" else tree_sitter_java.language()
        _PARSERS[language] = Parser(Language(grammar))
    return _PARSERS[language]


def _walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _text(node):
    return node.text.decode("utf-8", "replace") if node is not None and node.text else ""


def _line(node):
    return node.start_point[0] + 1


COMMENT_TYPES = {"comment", "line_comment", "block_comment"}
UNSAFE_C_CALLS = {
    "gets": ("critical", "`gets()` cannot limit input size and was removed from C++. Use `std::getline` or `fgets`."),
    "strcpy": ("warning", "`strcpy()` does not check buffer size (buffer overflow). Use `std::string` or `strncpy`."),
    "strcat": ("warning", "`strcat()` does not check buffer size (buffer overflow). Use `std::string` or `strncat`."),
    "sprintf": ("warning", "`sprintf()` can overflow its buffer. Use `snprintf` or `std::format`."),
}


def _statements(block):
    return [c for c in block.named_children if c.type not in COMMENT_TYPES]


def _condition_expression(node):
    """The expression inside if(...) / while(...)."""
    cond = node.child_by_field_name("condition")
    if cond is None:
        return None
    named = [c for c in cond.named_children if c.type not in COMMENT_TYPES]
    return named[0] if named else None


def _declared_identifier(declarator):
    """Find the variable name inside a declarator such as `x`, `x = 1`, `*p`, `a[5]`."""
    node = declarator
    for _ in range(6):
        if node is None:
            return None
        if node.type == "identifier":
            return node
        nxt = node.child_by_field_name("declarator") or node.child_by_field_name("name")
        node = nxt
    return None


def _analyze_tree_sitter(code, language):
    tree = _parser_for(language).parse(code.encode("utf-8"))
    if tree.root_node.has_error:
        return []  # syntax errors are reported by syntax_checker.py
    is_cpp = language == "C++"
    block_type = "compound_statement" if is_cpp else "block"
    function_types = {"function_definition"} if is_cpp else {"method_declaration", "constructor_declaration"}
    findings = []
    news = deletes = 0

    for node in _walk(tree.root_node):
        t = node.type

        # unsafe C library calls ------------------------------------------------
        if is_cpp and t == "call_expression":
            fn = _text(node.child_by_field_name("function"))
            if fn in UNSAFE_C_CALLS:
                severity, message = UNSAFE_C_CALLS[fn]
                findings.append(_finding(_line(node), severity, message, "unsafe-call"))
            elif fn == "scanf" and re.search(r'%s', _text(node.child_by_field_name("arguments"))):
                findings.append(_finding(_line(node), "warning",
                                         "`scanf(\"%s\")` has no width limit (buffer overflow). Use `%Ns` or `std::cin`.",
                                         "unsafe-call"))
        if is_cpp and t == "new_expression":
            news += 1
        if is_cpp and t == "delete_expression":
            deletes += 1

        # assignment used as a condition ---------------------------------------
        if t in ("if_statement", "while_statement"):
            expr = _condition_expression(node)
            if expr is not None and expr.type == "assignment_expression":
                findings.append(_finding(_line(node), "warning",
                                         "Assignment `=` inside a condition. Did you mean `==`?",
                                         "assignment-in-condition"))
            # while(true) without an exit
            if t == "while_statement" and expr is not None and _text(expr).strip() in ("true", "1"):
                leaves = any(
                    c.type in ("break_statement", "return_statement", "throw_statement")
                    or (c.type in ("call_expression", "method_invocation") and re.search(r"\b(exit|abort|_exit)\b", _text(c)))
                    for c in _walk(node)
                )
                if not leaves:
                    findings.append(_finding(_line(node), "warning",
                                             "`while (true)` has no break, return or throw, so it may never stop.",
                                             "infinite-loop"))

        # arithmetic ---------------------------------------------------------------
        if t == "binary_expression":
            op = _text(node.child_by_field_name("operator"))
            left, right = node.child_by_field_name("left"), node.child_by_field_name("right")
            if op in ("/", "%") and right is not None and _text(right).rstrip("lLfF") in ("0", "0.0"):
                findings.append(_finding(_line(node), "critical",
                                         "Division by zero: this fails at runtime.", "division-by-zero"))
            if not is_cpp and op in ("==", "!=") and (
                (left is not None and left.type == "string_literal")
                or (right is not None and right.type == "string_literal")
            ):
                findings.append(_finding(_line(node), "warning",
                                         "Strings compared with `==` compares references. Use `.equals()`.",
                                         "string-equality"))

        # empty catch ---------------------------------------------------------------
        if t == "catch_clause":
            body = next((c for c in node.children if c.type == block_type), None)
            if body is not None and not _statements(body):
                findings.append(_finding(_line(node), "warning",
                                         "Empty `catch` block: the error is silently ignored.",
                                         "empty-catch"))

        # unreachable code ------------------------------------------------------------
        if t == block_type:
            stmts = _statements(node)
            for i, stmt in enumerate(stmts[:-1]):
                if stmt.type in ("return_statement", "throw_statement", "break_statement", "continue_statement"):
                    findings.append(_finding(_line(stmts[i + 1]), "warning",
                                             f"Unreachable code after `{stmt.type.replace('_statement', '')}`.",
                                             "unreachable-code"))
                    break

        # unused local variables ----------------------------------------------------------
        if t in function_types:
            counts = {}
            for c in _walk(node):
                if c.type == "identifier":
                    counts[_text(c)] = counts.get(_text(c), 0) + 1
            for c in _walk(node):
                if is_cpp and c.type == "declaration":
                    type_node = c.child_by_field_name("type")
                    simple = type_node is not None and type_node.type in ("primitive_type", "sized_type_specifier")
                    declarators = c.children_by_field_name("declarator") if simple else []
                elif not is_cpp and c.type == "local_variable_declaration":
                    type_node = c.child_by_field_name("type")
                    simple = type_node is not None and (
                        type_node.type.endswith("_type") or _text(type_node) == "String"
                    ) and type_node.type != "generic_type"
                    declarators = c.children_by_field_name("declarator") if simple else []
                else:
                    continue
                for d in declarators:
                    ident = _declared_identifier(d)
                    if ident is not None and counts.get(_text(ident)) == 1 and not _text(ident).startswith("_"):
                        findings.append(_finding(_line(ident), "info",
                                                 f"Variable `{_text(ident)}` is declared but never used.",
                                                 "unused-variable"))

    # possible memory leak (heuristic, so worded carefully) -----------------------------
    if is_cpp and news > 0 and deletes == 0 and not re.search(
        r"unique_ptr|shared_ptr|make_unique|make_shared", code
    ):
        first = next(n for n in _walk(tree.root_node) if n.type == "new_expression")
        findings.append(_finding(_line(first), "warning",
                                 "Memory allocated with `new` but `delete` never appears: possible memory leak. "
                                 "Prefer `std::unique_ptr` or `std::vector`.", "possible-leak"))

    # unused imports (Java) -----------------------------------------------------------------
    if not is_cpp:
        for node in tree.root_node.children:
            if node.type != "import_declaration":
                continue
            text = _text(node)
            if text.rstrip(";").endswith("*") or "static" in text.split():
                continue
            name = text.rstrip(";").split(".")[-1].strip()
            rest = code.replace(text, "")
            if name and not re.search(rf"\b{re.escape(name)}\b", rest):
                findings.append(_finding(_line(node), "info", f"Import `{name}` is never used.", "unused-import"))
    return findings


# =====================================================================
#                              public API
# =====================================================================
def analyze_static(code, language):
    """Return a list of findings, sorted by line number."""
    if language == "Python":
        findings = _analyze_python(code)
    elif language in ("C++", "Java") and HAS_TREE_SITTER:
        findings = _analyze_tree_sitter(code, language)
    else:
        findings = []
    return sorted(findings, key=lambda f: (f["line"], f["rule"]))
