"""
TechSpecAnalyser — Transparent Multi-Factor Code Review Scoring Engine.
Calculates independent scores for:
  - Security (30%)
  - Correctness / Bugs (30%)
  - Maintainability (20%)
  - Complexity (20%)
Generates score deltas and explanations between review sessions.
"""
from typing import Any, Dict, List, Optional


def compute_multi_factor_score(
    findings: List[Dict[str, Any]],
    complexity_data: Optional[Dict[str, Any]] = None,
    ai_score: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Computes transparent component scores and weighted overall quality score.
    Returns: {
        "overall_score": float,
        "security_score": float,
        "correctness_score": float,
        "maintainability_score": float,
        "complexity_score": float,
        "breakdown": Dict[str, Any]
    }
    """
    complexity_data = complexity_data or {}
    penalties = []

    # 1. Security Score (Base: 10.0)
    sec_penalty = 0.0
    security_findings = [f for f in findings if f.get("source") == "static-security" or "cwe" in f]
    for sf in security_findings:
        sev = (sf.get("severity") or "info").lower()
        if sev == "critical":
            sec_penalty += 3.0
            penalties.append(f"Critical security vulnerability: {sf.get('title', 'CWE finding')} (-3.0 pts)")
        elif sev in ("high", "warning"):
            sec_penalty += 1.5
            penalties.append(f"Security warning: {sf.get('title', 'CWE finding')} (-1.5 pts)")
        elif sev == "medium":
            sec_penalty += 0.75
        else:
            sec_penalty += 0.25

    security_score = max(0.0, min(10.0, round(10.0 - sec_penalty, 1)))

    # 2. Correctness / Bugs Score (Base: 10.0)
    corr_penalty = 0.0
    bug_findings = [f for f in findings if f.get("source") != "static-security" and "cwe" not in f]
    for bf in bug_findings:
        sev = (bf.get("severity") or "info").lower()
        if sev == "critical":
            corr_penalty += 2.5
            penalties.append(f"Critical bug / syntax failure: {bf.get('description', '')[:40]} (-2.5 pts)")
        elif sev in ("high", "warning"):
            corr_penalty += 1.0
            penalties.append(f"Warning / logic issue: {bf.get('description', '')[:40]} (-1.0 pts)")
        else:
            corr_penalty += 0.25

    correctness_score = max(0.0, min(10.0, round(10.0 - corr_penalty, 1)))

    # 3. Maintainability Score (Derived from MI or Doc Coverage)
    mi = complexity_data.get("maintainability_index")
    if mi is not None:
        if mi >= 80:
            maint_score = 10.0
        elif mi >= 65:
            maint_score = 8.5
        elif mi >= 50:
            maint_score = 6.5
        else:
            maint_score = 4.0
    else:
        maint_score = 8.0  # neutral baseline when MI not applicable
    maintainability_score = round(maint_score, 1)

    # 4. Complexity Score (Derived from Cyclomatic Complexity)
    avg_cc = complexity_data.get("average_complexity", 1.0)
    rating = complexity_data.get("rating", "A")
    if avg_cc <= 5:
        comp_score = 10.0
    elif avg_cc <= 10:
        comp_score = 8.5
    elif avg_cc <= 20:
        comp_score = 6.0
    elif avg_cc <= 30:
        comp_score = 4.0
    else:
        comp_score = 2.0
    complexity_score = round(comp_score, 1)

    # Weighted Overall Score (30% Security, 30% Correctness, 20% Maintainability, 20% Complexity)
    deterministic_score = (
        0.30 * security_score
        + 0.30 * correctness_score
        + 0.20 * maintainability_score
        + 0.20 * complexity_score
    )

    # Blend with AI opinion if available (85% deterministic facts + 15% AI subjective judgment)
    if ai_score is not None:
        final_score = round(0.85 * deterministic_score + 0.15 * float(ai_score), 1)
    else:
        final_score = round(deterministic_score, 1)

    final_score = max(0.0, min(10.0, final_score))

    return {
        "overall_score": final_score,
        "security_score": security_score,
        "correctness_score": correctness_score,
        "maintainability_score": maintainability_score,
        "complexity_score": complexity_score,
        "ai_score": ai_score,
        "penalties": penalties,
        "weights": {
            "security": "30%",
            "correctness": "30%",
            "maintainability": "20%",
            "complexity": "20%",
        },
    }


def explain_score_delta(
    old_record: Dict[str, Any],
    new_record: Dict[str, Any],
) -> Dict[str, Any]:
    """Explains why the score changed between two review sessions."""
    old_score = old_record.get("overall_score", 0.0)
    new_score = new_record.get("overall_score", 0.0)
    delta = round(new_score - old_score, 1)

    old_crit = old_record.get("critical_count", 0)
    new_crit = new_record.get("critical_count", 0)
    old_warn = old_record.get("warning_count", 0)
    new_warn = new_record.get("warning_count", 0)

    reasons = []
    if delta > 0:
        summary = f"Quality improved by +{delta} points."
    elif delta < 0:
        summary = f"Quality decreased by {delta} points."
    else:
        summary = "Quality score remained identical."

    if new_crit < old_crit:
        reasons.append(f"Resolved {old_crit - new_crit} critical issue(s).")
    elif new_crit > old_crit:
        reasons.append(f"Introduced {new_crit - old_crit} new critical issue(s).")

    if new_warn < old_warn:
        reasons.append(f"Fixed {old_warn - new_warn} warning(s).")
    elif new_warn > old_warn:
        reasons.append(f"Introduced {new_warn - old_warn} new warning(s).")

    return {
        "delta": delta,
        "direction": "up" if delta > 0 else "down" if delta < 0 else "equal",
        "summary": summary,
        "reasons": reasons,
    }
