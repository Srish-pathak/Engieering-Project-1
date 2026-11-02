"""
Complexity analysis.

Every result states HOW the number was produced:

  "measured"  : a real tool computed it
                 - Python   -> radon (AST based cyclomatic complexity + Maintainability Index)
                 - C++/Java -> lizard (token based cyclomatic complexity)
  "estimated" : a keyword-counting heuristic, used only when no function could be
                 detected (for example a loose snippet). Treat it as a rough guide.

Cyclomatic complexity (CC) = number of independent paths through a function.
A function with no branches has CC = 1; every `if`, loop, `case`, `&&`, `||` adds 1.
"""
import re

from radon.complexity import cc_visit
from radon.metrics import mi_rank, mi_visit
from radon.raw import analyze as raw_analyze
from radon.visitors import Function

try:
    import lizard

    HAS_LIZARD = True
except ImportError:
    HAS_LIZARD = False

RANK_LABELS = {
    "A": "Simple, low risk",
    "B": "Moderate, well structured",
    "C": "Complex, consider splitting",
    "D": "Very complex, hard to test",
    "E": "Extremely complex",
    "F": "Unmaintainable, refactor now",
}
MI_LABELS = {
    "A": "Highly maintainable",
    "B": "Moderately maintainable",
    "C": "Hard to maintain",
}
CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "else", "do"}
FILE_NAMES = {"C++": "submission.cpp", "Java": "Submission.java"}


def rank_letter(complexity):
    for limit, letter in ((5, "A"), (10, "B"), (20, "C"), (30, "D"), (40, "E")):
        if complexity <= limit:
            return letter
    return "F"


def _empty(method, note, error=None):
    return {
        "method": method, "analysis_type": "measured", "average_complexity": 0,
        "max_complexity": 0, "rating": "N/A", "rating_label": "", "details": [],
        "maintainability_index": None, "mi_rank": None, "mi_label": "", "lines": {},
        "note": note, "error": error,
    }


def _summary(method, analysis_type, rows, mi, note, lines=None):
    complexities = [r["complexity"] for r in rows] or [1]
    average = round(sum(complexities) / len(complexities), 2)
    worst = max(complexities)
    mi_letter = mi_rank(mi) if mi is not None else None
    return {
        "method": method,
        "analysis_type": analysis_type,
        "average_complexity": average,
        "max_complexity": worst,
        "rating": rank_letter(average),
        "rating_label": RANK_LABELS[rank_letter(average)],
        "details": rows,
        "maintainability_index": mi,
        "mi_rank": mi_letter,
        "mi_label": MI_LABELS.get(mi_letter, ""),
        "lines": lines or {},
        "note": note,
        "error": None,
    }


# ---------------------------------------------------------------- Python
def _analyze_python(code):
    try:
        blocks = [b for b in cc_visit(code) if isinstance(b, Function)]
    except SyntaxError as e:
        return _empty("radon", "Fix the syntax error to measure complexity.", f"Syntax error: {e}")

    rows = [
        {
            "name": b.fullname, "line": b.lineno, "complexity": b.complexity,
            "rank": rank_letter(b.complexity),
        }
        for b in sorted(blocks, key=lambda b: b.lineno)
    ]
    try:
        mi = round(mi_visit(code, multi=True), 2)
    except Exception:
        mi = None
    try:
        raw = raw_analyze(code)
        lines = {"Total lines": raw.loc, "Code lines": raw.sloc, "Comment lines": raw.comments, "Blank lines": raw.blank}
    except Exception:
        lines = {}
    note = (
        "Measured with radon. Cyclomatic complexity and the Maintainability Index "
        "(0-100, higher is better) are exact calculations, not estimates."
    )
    if not rows:
        note += " No functions were found, so the module counts as complexity 1."
    return _summary("radon", "measured", rows, mi, note, lines)


# ------------------------------------------------------------ C++ / Java
def _analyze_with_lizard(code, language):
    result = lizard.analyze_file.analyze_source_code(FILE_NAMES[language], code)
    rows = [
        {
            "name": f.name, "line": f.start_line, "complexity": f.cyclomatic_complexity,
            "rank": rank_letter(f.cyclomatic_complexity),
        }
        for f in result.function_list
        if f.name.split("::")[-1] not in CONTROL_KEYWORDS  # lizard can mistake `if (...) {` for a function
    ]
    lines = {"Code lines (NLOC)": result.nloc, "Functions": len(rows)}
    return rows, lines


def _estimate(code):
    """Keyword heuristic. Comments and strings are removed first."""
    cleaned = re.sub(r"//.*?$|/\*.*?\*/", " ", code, flags=re.S | re.M)
    cleaned = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', cleaned)
    keywords = re.findall(r"\b(?:if|for|while|case|catch)\b|&&|\|\||\?", cleaned)
    depth = peak = 0
    for ch in cleaned:
        if ch == "{":
            depth += 1
            peak = max(peak, depth)
        elif ch == "}":
            depth = max(0, depth - 1)
    return 1 + len(keywords), len(keywords), peak


def _analyze_c_like(code, language):
    rows, lines = [], {}
    if HAS_LIZARD:
        try:
            rows, lines = _analyze_with_lizard(code, language)
        except Exception:
            rows = []
    if rows:
        note = (
            "Measured with lizard, which counts decision points (if, loops, case, catch, &&, ||, ?) "
            "in every function. The Maintainability Index is only available for Python."
        )
        return _summary("lizard", "measured", rows, None, note, lines)

    total, branches, depth = _estimate(code)
    rows = [
        {"name": "estimated total", "line": 1, "complexity": total, "rank": rank_letter(total)},
    ]
    note = (
        "ESTIMATE: no function could be detected, so complexity was approximated by counting "
        f"{branches} branch keywords (max nesting depth {depth}). Wrap the code in a function for a measured result."
    )
    return _summary("keyword heuristic", "estimated", rows, None, note, {})


# ------------------------------------------------------------------ public
def analyze_complexity(code, language):
    if not code or not code.strip():
        return _empty("none", "No code to analyze.")
    if language == "Python":
        return _analyze_python(code)
    return _analyze_c_like(code, language)
