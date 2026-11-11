"""
TechSpecAnalyser — Export Utilities.
Provides Markdown, JSON, HTML, and CSV export builders, unified diffs, and filename stems.
"""
import difflib
import html
import json
from datetime import datetime
from typing import Any, Dict, Optional

from config import APP_NAME
from reports.json_report import generate_csv_findings, generate_json_report
from reports.markdown_report import generate_markdown_report


def file_stem(language: str = "project") -> str:
    """Generates timestamped filename stem."""
    lang_clean = language.lower().replace("+", "p").replace("/", "_").replace(" ", "_")
    return f"techspec_report_{lang_clean}_{datetime.now():%Y%m%d_%H%M}"


def unified_diff(before: str, after: str, from_name: str = "original", to_name: str = "improved") -> str:
    """Generates a clean unified diff string."""
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=from_name,
            tofile=to_name,
            n=2,
        )
    )


def build_markdown(result: Dict[str, Any], complexity: Optional[Dict] = None, code: str = "", language: str = "") -> str:
    """Markdown builder compatible with legacy and modern signatures."""
    merged = dict(result)
    if complexity:
        merged["complexity"] = complexity
    if language:
        merged["language"] = language
    return generate_markdown_report(merged)


def build_json(result: Dict[str, Any], complexity: Optional[Dict] = None, code: str = "", language: str = "") -> str:
    """JSON export builder."""
    merged = dict(result)
    if complexity:
        merged["complexity"] = complexity
    return generate_json_report(merged)


def build_csv(result: Dict[str, Any]) -> str:
    """CSV export builder."""
    return generate_csv_findings(result)


def build_html(result: Dict[str, Any], complexity: Optional[Dict] = None, code: str = "", language: str = "") -> str:
    """Builds a standalone styled HTML report."""
    name = html.escape(str(result.get("repo_full_name") or result.get("project_name") or APP_NAME))
    score = result.get("overall_score", 0.0)
    summary = html.escape(str(result.get("summary", "")))
    crit = result.get("critical_count", 0)
    warn = result.get("warning_count", 0)

    findings_html = []
    for f in result.get("bugs", []) + result.get("security_findings", []):
        sev = html.escape(str(f.get("severity", "info")).upper())
        desc = html.escape(str(f.get("description", "")))
        file_path = html.escape(str(f.get("file", "code")))
        line = html.escape(str(f.get("line", "1")))
        findings_html.append(
            f"<tr><td><span class='badge {sev.lower()}'>{sev}</span></td>"
            f"<td><code>{file_path}:{line}</code></td><td>{desc}</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{name} — Review Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0B1020; color: #E7EBFA; padding: 2rem; }}
.card {{ background: #131A33; border: 1px solid #263056; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }}
h1, h2 {{ color: #4FD1E8; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
th, td {{ text-align: left; padding: 0.75rem; border-bottom: 1px solid #263056; }}
th {{ color: #98A2C8; }}
.badge {{ padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: bold; font-size: 0.8rem; }}
.critical {{ background: #FF6B7A; color: #0B1020; }}
.warning {{ background: #FFC857; color: #0B1020; }}
.info {{ background: #7AA7FF; color: #0B1020; }}
code {{ font-family: Consolas, monospace; background: #0A0F22; padding: 0.2rem 0.4rem; border-radius: 4px; }}
</style>
</head>
<body>
<div class="card">
<h1>{name}</h1>
<p><strong>Overall Score:</strong> {score}/10 | <strong>Critical:</strong> {crit} | <strong>Warnings:</strong> {warn}</p>
<p>{summary}</p>
</div>
<div class="card">
<h2>Findings ({len(findings_html)})</h2>
<table>
<thead><tr><th>Severity</th><th>Location</th><th>Description</th></tr></thead>
<tbody>
{''.join(findings_html) if findings_html else '<tr><td colspan="3">No findings reported.</td></tr>'}
</tbody>
</table>
</div>
</body>
</html>"""
