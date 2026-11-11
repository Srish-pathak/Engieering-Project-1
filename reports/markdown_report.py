"""
TechSpecAnalyser — Markdown Report Exporter.
Generates comprehensive GitHub Flavored Markdown review reports.
"""
from typing import Any, Dict, List


def generate_markdown_report(data: Dict[str, Any]) -> str:
    """Builds a formatted Markdown report from review session data."""
    name = data.get("repo_full_name") or data.get("project_name") or "CodeLens Review"
    time_str = data.get("time", "N/A")
    score = data.get("overall_score", 0.0)
    summary = data.get("summary", "")
    crit = data.get("critical_count", 0)
    warn = data.get("warning_count", 0)
    info = data.get("info_count", 0)

    scores = data.get("scores") or {}
    sec_score = scores.get("security_score", "N/A")
    corr_score = scores.get("correctness_score", "N/A")
    maint_score = scores.get("maintainability_score", "N/A")
    comp_score = scores.get("complexity_score", "N/A")

    lines = [
        f"# TechSpecAnalyser Review Report — {name}",
        "",
        f"> **Generated at:** {time_str} | **Overall Quality Score:** {score}/10",
        "",
        "## 1. Executive Summary",
        summary,
        "",
        "### Score Breakdown",
        f"- **Security Score:** {sec_score}/10",
        f"- **Correctness / Bugs:** {corr_score}/10",
        f"- **Maintainability:** {maint_score}/10",
        f"- **Complexity:** {comp_score}/10",
        "",
        "### Findings Overview",
        f"- **Critical Issues:** {crit}",
        f"- **Warnings:** {warn}",
        f"- **Informational / Style:** {info}",
        "",
        "## 2. Security Findings",
    ]

    sec_findings = data.get("security_findings", [])
    if sec_findings:
        lines.append("| Severity | File | Line | CWE | Issue Title | Description |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for sf in sec_findings:
            lines.append(
                f"| `{sf.get('severity', '').upper()}` | `{sf.get('file', 'N/A')}` | {sf.get('line', 'N/A')} | "
                f"`{sf.get('cwe', 'N/A')}` | {sf.get('title', 'Security Finding')} | {sf.get('description', '')} |"
            )
    else:
        lines.append("No critical security vulnerabilities detected.")

    lines.extend([
        "",
        "## 3. Bugs & Logic Findings",
    ])

    bugs = data.get("bugs", [])
    if bugs:
        lines.append("| Severity | File | Line | Source | Description | Suggested Fix |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for b in bugs:
            lines.append(
                f"| `{b.get('severity', '').upper()}` | `{b.get('file', 'N/A')}` | {b.get('line', 'N/A')} | "
                f"`{b.get('source', 'static')}` | {b.get('description', '')} | {b.get('fix', 'Review logic')} |"
            )
    else:
        lines.append("No syntax or deterministic bugs detected.")

    # Improvements
    improvements = data.get("improvements", [])
    if improvements:
        lines.extend([
            "",
            "## 4. Optimization & Improvement Recommendations",
        ])
        for imp in improvements:
            lines.append(f"- **{imp.get('title', 'Recommendation')}:** {imp.get('detail', '')}")

    lines.extend([
        "",
        "---",
        "*Report generated automatically by TechSpecAnalyser — Code Review & Security Intelligence Platform.*",
    ])

    return "\n".join(lines)
