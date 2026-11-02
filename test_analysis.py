"""Tests for the offline analyzers: syntax, static analysis, complexity, scoring, history."""
import pytest

from complexity import analyze_complexity
from samples import SAMPLES
from static_analysis import analyze_static
from syntax_checker import check_syntax
import utils


def rules(code, language="Python"):
    return [f["rule"] for f in analyze_static(code, language)]


# ---------------------------------------------------------------- syntax
def test_syntax_python_valid():
    assert check_syntax("x = 1\n", "Python") == {"valid": True, "bugs": [], "checker": "python compiler"}


def test_syntax_python_error_returns_list_with_line():
    r = check_syntax("def f(:\n    pass\n", "Python")
    assert r["valid"] is False and isinstance(r["bugs"], list) and r["bugs"][0]["line"] == 1


def test_syntax_python_return_outside_function():
    assert not check_syntax("return 1", "Python")["valid"]


def test_syntax_python_indentation_error():
    assert not check_syntax("def f():\nx = 1\n", "Python")["valid"]


def test_syntax_cpp_missing_semicolon_has_line_number():
    r = check_syntax("int add(int a, int b) {\n    return a + b\n}\n", "C++")
    assert not r["valid"] and r["bugs"][0]["line"] == 2


def test_syntax_cpp_valid():
    assert check_syntax("int main() { return 0; }", "C++")["valid"]


def test_syntax_java_missing_semicolon():
    r = check_syntax("public class A {\n void f() {\n int x = 1\n }\n}\n", "Java")
    assert not r["valid"] and r["bugs"][0]["line"] == 3


def test_syntax_java_method_outside_class():
    assert not check_syntax("int add(int a) { return a; }", "Java")["valid"]


def test_syntax_java_valid():
    assert check_syntax("public class A { void f() { } }", "Java")["valid"]


# ------------------------------------------------- static: argument checking
def test_arity_missing_argument():
    assert "bad-call" in rules("def add(a, b):\n    return a + b\nadd(1)\n")


def test_arity_too_many_arguments():
    assert "bad-call" in rules("def add(a, b):\n    return a + b\nadd(1, 2, 3)\n")


@pytest.mark.parametrize("call", ["f(1)", "f(1, 2)", "f(1, b=2)", "f(a=1)", "f(*args)", "f(**kw)", "f(1, *rest)"])
def test_arity_no_false_positive(call):
    code = f"def f(a, b=5):\n    return a + b\nargs = (1,)\nrest = [2]\nkw = {{'a': 1}}\n{call}\n"
    assert "bad-call" not in rules(code)


def test_arity_unexpected_keyword():
    assert "bad-call" in rules("def f(a):\n    return a\nf(1, z=2)\n")


def test_arity_varargs_accepts_anything():
    assert "bad-call" not in rules("def f(*a, **k):\n    return a\nf(1, 2, 3, x=4)\n")


def test_arity_keyword_only_required():
    assert "bad-call" in rules("def f(a, *, c):\n    return a\nf(1)\n")


def test_arity_skips_redefined_and_decorated():
    redefined = "def f(a):\n    return a\ndef f(a, b):\n    return a\nf(1, 2)\n"
    decorated = "import functools\n@functools.cache\ndef f(a):\n    return a\nf(1)\n"
    assert "bad-call" not in rules(redefined)
    assert "bad-call" not in rules(decorated)


def test_arity_ignores_methods():
    code = "class A:\n    def go(self, x):\n        return x\n\ndef go():\n    return 1\ngo()\n"
    assert "bad-call" not in rules(code)


# ------------------------------------------------------ static: other rules
def test_undefined_name_detected_and_builtins_ok():
    assert "undefined-name" in rules("print(totl)\n")
    assert "undefined-name" not in rules("x = [1]\nprint(len(x), sum(x))\n")


def test_undefined_name_ignores_comprehension_and_lambda_and_except():
    code = "r = [i*2 for i in range(3)]\nf = lambda q: q+1\ntry:\n    pass\nexcept ValueError as err:\n    print(err)\nprint(r, f)\n"
    assert "undefined-name" not in rules(code)


def test_mutable_default():
    assert "mutable-default" in rules("def f(x=[]):\n    return x\n")


def test_bare_except_and_swallowed():
    assert "bare-except" in rules("try:\n    pass\nexcept:\n    print(1)\n")
    assert "swallowed-exception" in rules("try:\n    pass\nexcept ValueError:\n    pass\n")


def test_unused_import_and_variable():
    r = rules("import os\ndef f():\n    y = 1\n    return 2\n")
    assert "unused-import" in r and "unused-variable" in r


def test_used_import_and_variable_not_flagged():
    assert rules("import os\ndef f():\n    y = os.getcwd()\n    return y\n") == []


def test_division_by_zero_and_unreachable_and_infinite_loop():
    assert "division-by-zero" in rules("x = 5 / 0\n")
    assert "unreachable-code" in rules("def f():\n    return 1\n    print(2)\n")
    assert "infinite-loop" in rules("while True:\n    pass\n")
    assert "infinite-loop" not in rules("while True:\n    break\n")


def test_none_comparison_and_is_literal():
    r = rules("x = 1\nif x == None: pass\nif x is 5: pass\n")
    assert "none-comparison" in r and "is-literal" in r


def test_static_returns_nothing_for_broken_syntax():
    assert analyze_static("def f(:", "Python") == []


def test_cpp_rules():
    code = ('int main() { char b[4]; strcpy(b, "x"); int y = 3 / 0; if (y = 2) {} '
            'int* p = new int; try { } catch (...) { } while (true) { } return 0; y = 1; }')
    r = rules(code, "C++")
    for expected in ("unsafe-call", "division-by-zero", "assignment-in-condition", "possible-leak",
                     "empty-catch", "infinite-loop", "unreachable-code"):
        assert expected in r


def test_cpp_smart_pointer_not_flagged_as_leak():
    assert "possible-leak" not in rules("int main() { auto p = std::make_unique<int>(3); return *p; }", "C++")


def test_java_rules():
    code = ('import java.util.List;\npublic class A { boolean f(String s) { if (s == "a") { return true; } '
            'try { } catch (Exception e) { } int z = 1 / 0; return false; } }')
    r = rules(code, "Java")
    for expected in ("unused-import", "string-equality", "empty-catch", "division-by-zero"):
        assert expected in r


def test_java_equals_not_flagged():
    assert "string-equality" not in rules('public class A { boolean f(String s) { return s.equals("a"); } }', "Java")


def test_clean_samples_have_no_findings():
    for lang, cases in SAMPLES.items():
        assert analyze_static(cases["Clean code"], lang) == [], lang


# ------------------------------------------------------------- complexity
def test_complexity_python_measured_with_mi():
    r = analyze_complexity("def f(x):\n    if x:\n        return 1\n    return 2\n", "Python")
    assert r["analysis_type"] == "measured" and r["method"] == "radon"
    assert r["max_complexity"] == 2 and r["maintainability_index"] is not None


def test_complexity_python_syntax_error_is_reported_not_raised():
    assert analyze_complexity("def f(:", "Python")["error"]


def test_complexity_c_like_measured_with_lizard():
    r = analyze_complexity("int f(int a) { if (a > 1 && a < 5) { return 1; } return 0; }", "C++")
    assert r["analysis_type"] == "measured" and r["max_complexity"] == 3 and r["maintainability_index"] is None


def test_complexity_loose_snippet_is_labelled_estimate():
    r = analyze_complexity("if (x > 1) { y(); }", "Java")
    assert r["analysis_type"] == "estimated"


def test_complexity_rank_letters():
    assert [utils._rank_for(v) for v in (1, 6, 11, 21, 31, 50)] == list("ABCDEF")


# ---------------------------------------------------------------- utils
def test_json_parse_fenced_and_clamped():
    r = utils.safe_json_parse('```json\n{"summary": "ok", "overall_score": 99}\n```')
    assert r["overall_score"] == 10 and r["bugs"] == []


@pytest.mark.parametrize("raw", ["", "not json", "[1, 2]", None])
def test_json_parse_bad_input_returns_error_dict(raw):
    assert utils.safe_json_parse(raw)["error"] is True


def test_severity_aliases_normalised():
    assert utils.normalize_bug({"severity": "High"})["severity"] == "critical"
    assert utils.normalize_bug({"severity": "weird"})["severity"] == "info"


def test_merge_bugs_dedupes_and_sorts():
    local = [{"line": 3, "severity": "info", "description": "Name x is not defined", "source": "static"}]
    ai = [{"line": "3", "severity": "critical", "description": "x is not defined"},
          {"line": 1, "severity": "critical", "description": "Something else"}]
    merged = utils.merge_bugs(local, ai)
    assert len(merged) == 2 and merged[0]["severity"] == "critical"


def test_score_clean_code_is_ten_and_buggy_is_lower():
    assert utils.compute_quality_score([], {"max_complexity": 1, "mi_rank": "A"})["score"] == 10
    bad = [{"severity": "critical"}] * 3
    assert utils.compute_quality_score(bad, None)["score"] == 4.0


def test_score_blends_ai_opinion():
    assert utils.compute_quality_score([], None, ai_score=5)["score"] == 8.0  # 0.6*10 + 0.4*5


def test_score_label_and_colour_agree():
    for s in (1, 4.9, 5, 6.9, 7, 8.4, 8.5, 10):
        label, color = utils.score_band(s)
        assert utils.score_label(s) == label and utils.score_color(s) == color


def test_history_roundtrip_and_corruption(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "HISTORY_FILE", tmp_path / "h.json")
    entry = utils.make_history_entry("Python", "x=1", {"bugs": [], "overall_score": 9, "summary": "s"}, {})
    entries = utils.add_history([], entry)
    assert utils.load_history()[0]["id"] == entries[0]["id"]
    (tmp_path / "h.json").write_text("{broken", encoding="utf-8")
    assert utils.load_history() == []
    assert utils.clear_history() == []


def test_history_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "HISTORY_FILE", tmp_path / "h.json")
    entries = []
    for i in range(utils.HISTORY_LIMIT + 5):
        entries = utils.add_history(entries, {"id": str(i)})
    assert len(entries) == utils.HISTORY_LIMIT


def test_history_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, "HISTORY_FILE", tmp_path / "h.json")
    monkeypatch.setenv("TECSPACE_SAVE_HISTORY", "0")
    utils.add_history([], {"id": "1"})
    assert not (tmp_path / "h.json").exists()


def test_merge_keeps_different_bugs_on_the_same_line():
    local = [{"line": 5, "severity": "critical", "description": "Division by zero: this raises ZeroDivisionError.", "source": "static"}]
    ai = [{"line": 5, "severity": "warning", "description": "Variable name `r` is too short to be readable"}]
    assert len(utils.merge_bugs(local, ai)) == 2


def test_merge_drops_reworded_duplicate():
    local = [{"line": 4, "severity": "critical", "description": "Call to `add(a, b)` is wrong: missing required argument(s): b.", "source": "static"}]
    ai = [{"line": "4", "severity": "critical", "description": "add() is called with one argument"}]
    assert len(utils.merge_bugs(local, ai)) == 1
