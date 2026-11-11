"""
TechSpecAnalyser — Report Exporters & Diff Test Suite.
Tests Markdown, JSON, and CSV export generators and unified diffs.
"""
from reports.export import build_csv, build_json, build_markdown, file_stem, unified_diff


def test_markdown_and_json_report_generation():
    data = {
        "repo_full_name": "developer/demo",
        "time": "10 Nov 2026, 12:00",
        "overall_score": 8.5,
        "summary": "High quality implementation with 1 warning.",
        "scores": {
            "security_score": 10.0,
            "correctness_score": 8.0,
            "maintainability_score": 9.0,
            "complexity_score": 7.0,
        },
        "bugs": [
            {"file": "app.py", "line": 12, "severity": "warning", "description": "Unused import", "fix": "Remove import", "source": "static"}
        ],
        "security_findings": [],
        "improvements": [
            {"title": "Type annotations", "detail": "Add PEP 484 annotations"}
        ],
    }

    # Markdown
    md = build_markdown(data)
    assert "# TechSpecAnalyser Review Report" in md
    assert "developer/demo" in md
    assert "8.5/10" in md
    assert "Unused import" in md
    assert "Type annotations" in md

    # JSON
    js = build_json(data)
    assert '"overall_score": 8.5' in js
    assert '"developer/demo"' in js

    # CSV
    csv_text = build_csv(data)
    assert "Category,Severity,File,Line" in csv_text
    assert "app.py" in csv_text
    assert "Unused import" in csv_text


def test_unified_diff_generation():
    orig = "def add(a, b):\n    return a + b\n"
    fixed = "def add(a: int, b: int) -> int:\n    return a + b\n"

    diff = unified_diff(orig, fixed)
    assert "-def add(a, b):" in diff
    assert "+def add(a: int, b: int) -> int:" in diff


def test_file_stem_formatting():
    stem = file_stem("Python")
    assert stem.startswith("techspec_report_python_")
