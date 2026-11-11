"""
TechSpecAnalyser — Multi-Language Analyzers Test Suite.
Tests syntax checking, static rules, and complexity calculation across
Python, C/C++, Java, JavaScript, TypeScript, and Web markup.
"""
import pytest
from analyzers.static_analysis import analyze_static, get_analyzer, get_supported_languages
from analyzers.syntax_checker import check_syntax
from config import detect_language


def test_supported_languages_list():
    langs = get_supported_languages()
    assert "Python" in langs
    assert "C++" in langs
    assert "Java" in langs
    assert "JavaScript" in langs
    assert "TypeScript" in langs
    assert "HTML" in langs
    assert "CSS" in langs


def test_detect_language_by_extension():
    assert detect_language("app.py") == "Python"
    assert detect_language("server.ts") == "TypeScript"
    assert detect_language("Component.tsx") == "TSX"
    assert detect_language("script.js") == "JavaScript"
    assert detect_language("main.cpp") == "C++"
    assert detect_language("header.hpp") == "C++"
    assert detect_language("Main.java") == "Java"
    assert detect_language("index.html") == "HTML"
    assert detect_language("styles.scss") == "SCSS"
    assert detect_language("unknown.xyz") == "Unknown"


def test_python_syntax_and_static_rules():
    py_analyzer = get_analyzer("Python")
    assert "Deterministic AST Parser (ast.parse)" in py_analyzer.supported_checks

    # Valid code
    syntax = py_analyzer.check_syntax("def add(a, b):\n    return a + b\n")
    assert syntax["valid"] is True
    assert len(syntax["bugs"]) == 0

    # Broken syntax
    syntax_bad = py_analyzer.check_syntax("def add(a, b\n    return a + b\n")
    assert syntax_bad["valid"] is False
    assert len(syntax_bad["bugs"]) > 0

    # Bug: Mutable default
    bugs = py_analyzer.analyze_bugs("def append_item(x, target=[]):\n    target.append(x)\n    return target\n")
    assert any(b.get("rule") == "mutable-default" for b in bugs)


def test_javascript_and_typescript_rules():
    js_analyzer = get_analyzer("JavaScript")
    ts_analyzer = get_analyzer("TypeScript")

    # Loose equality check in JS
    js_code = "function check(x) {\n  if (x == 0) return true;\n  debugger;\n  return false;\n}"
    js_bugs = js_analyzer.analyze_bugs(js_code)
    assert any(b.get("rule") == "loose-equality" for b in js_bugs)
    assert any(b.get("rule") == "debugger-statement" for b in js_bugs)

    # TypeScript @ts-ignore check
    ts_code = "// @ts-ignore\nconst data: any = JSON.parse(str);\nconst name = data!.user!.name;\n"
    ts_bugs = ts_analyzer.analyze_bugs(ts_code)
    assert any(b.get("rule") == "suppressed-type-check" for b in ts_bugs)
    assert any(b.get("rule") == "unsafe-any-type" for b in ts_bugs)
    assert any(b.get("rule") == "non-null-assertion" for b in ts_bugs)


def test_web_analyzer_html_and_css():
    web_analyzer = get_analyzer("HTML")

    # HTML missing alt tag
    html_code = "<div><img src='logo.png'><center>Deprecated</center></div>"
    html_bugs = web_analyzer.analyze_bugs(html_code, file_path="index.html")
    assert any(b.get("rule") == "img-missing-alt" for b in html_bugs)
    assert any(b.get("rule") == "deprecated-html-element" for b in html_bugs)

    # CSS unmatched braces
    css_bad = ".container { color: red; "
    css_syntax = web_analyzer.check_syntax(css_bad, file_path="styles.css")
    assert css_syntax["valid"] is False
