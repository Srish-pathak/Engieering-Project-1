"""
TechSpecAnalyser — Scoring Engine Test Suite.
Tests transparent 4-pillar scoring, weighting formulas, and delta explanations.
"""
from core.scoring import compute_multi_factor_score, explain_score_delta


def test_clean_code_scores_ten():
    scores = compute_multi_factor_score(findings=[], complexity_data={"average_complexity": 1.0, "maintainability_index": 95.0})
    assert scores["overall_score"] == 10.0
    assert scores["security_score"] == 10.0
    assert scores["correctness_score"] == 10.0
    assert scores["maintainability_score"] == 10.0
    assert scores["complexity_score"] == 10.0


def test_critical_security_finding_penalizes_score():
    findings = [
        {"severity": "critical", "source": "static-security", "title": "SQL Injection", "cwe": "CWE-89"}
    ]
    scores = compute_multi_factor_score(findings=findings)
    assert scores["security_score"] == 7.0  # 10 - 3.0
    assert scores["overall_score"] < 10.0


def test_critical_bugs_penalizes_correctness():
    findings = [
        {"severity": "critical", "source": "static", "title": "Syntax Error", "description": "compile error"}
    ]
    scores = compute_multi_factor_score(findings=findings)
    assert scores["correctness_score"] == 7.5  # 10 - 2.5


def test_score_delta_explanation():
    old_run = {"overall_score": 6.5, "critical_count": 2, "warning_count": 4}
    new_run = {"overall_score": 8.5, "critical_count": 0, "warning_count": 2}

    delta = explain_score_delta(old_run, new_run)
    assert delta["delta"] == 2.0
    assert delta["direction"] == "up"
    assert any("Resolved 2 critical" in r for r in delta["reasons"])
    assert any("Fixed 2 warning" in r for r in delta["reasons"])
