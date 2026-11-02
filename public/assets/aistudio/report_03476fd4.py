"""Builds downloadable review reports (Markdown, standalone HTML, JSON)."""
import difflib
import html
import json
from datetime import datetime

from utils import APP_NAME, SEVERITY_STYLE, SOURCE_LABELS, count_by_severity, score_label


def _stamp():
    return datetime.now().strftime("%d %B %Y, %H:%M")


def file_stem(language):
    return f"tecspace_report_{language.lower().replace('+', 'p')}_{datetime.now():%Y%m%d_%H%M}"


def unified_diff(before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="original", tofile="improved", n=2,
        )
    )


def build_markdown(result, complexity, code, language) -> str:
    counts = count_by_severity(result.get("bugs", []))
    score = result.get("overall_score", 0)
    out = [
        f"# {APP_NAME} - Code Review Report",
        f"*{language} | generated {_stamp()}*",
        "",
        f"## Overall score: {score}/10 ({score_label(score)})",
        f"Critical: **{counts['critical']}** | Warnings: **{counts['warning']}** | Info: **{counts['info']}**",
        "",
        "## Summary",
        result.get("summary") or "No summary.",
        "",
    ]
    if result.get("ai_status") == "failed":
        out += [f"> AI review was unavailable: {result.get('ai_error')}", ""]

    out.append("## Issues")
    if not result.get("bugs"):
        out.append("No issues found.")
    for b in result.get("bugs", []):
        source = SOURCE_LABELS.get(b.get("source"), b.get("source", ""))
        out.append(f"- **{SEVERITY_STYLE[b['severity']]['label']}** (line {b['line']}, {source}): {b['description']}")
        if b.get("fix"):
            out.append(f"  - Fix: {b['fix']}")
    out += ["", "## Improvements"]
    for i in result.get("improvements", []) or []:
        out.append(f"- **{i['title']}**: {i['detail']}")
    if not result.get("improvements"):
        out.append("None provided.")

    if complexity:
        out += [
            "", "## Complexity",
            f"- Method: {complexity['method']} ({complexity['analysis_type']})",
            f"- Average cyclomatic complexity: {complexity['average_complexity']} (rating {complexity['rating']})",
            f"- Highest function complexity: {complexity['max_complexity']}",
        ]
        if complexity.get("maintainability_index") is not None:
            out.append(f"- Maintainability index: {complexity['maintainability_index']} ({complexity['mi_label']})")
        if complexity.get("details"):
            out += ["", "| Function | Line | Complexity | Rank |", "|---|---|---|---|"]
            out += [f"| {d['name']} | {d['line']} | {d['complexity']} | {d['rank']} |" for d in complexity["details"]]
        out += ["", result.get("complexity_notes") or ""]

    details = result.get("score_details") or {}
    if details:
        out += ["", "## How the score was calculated", f"- Rule-based score: {details.get('rule_score')}/10"]
        for p in details.get("penalties", []):
            out.append(f"  - -{p['points']} for {p['label']}")
        if details.get("ai_score") is not None:
            out.append(f"- AI opinion: {details['ai_score']}/10 (final = 60% rules + 40% AI)")

    fence = "```"
    out += ["", "## Reviewed code", f"{fence}{language.lower()}", code.rstrip(), fence]
    if result.get("improved_code"):
        out += ["", "## AI-improved code", f"{fence}{language.lower()}", result["improved_code"].rstrip(), fence]
        if result.get("improved_code_valid") is False:
            out.append("> Warning: automatic checks found problems in the improved code. Review it before using it.")
    return "\n".join(out) + "\n"


def build_html(result, complexity, code, language) -> str:
    e = html.escape
    counts = count_by_severity(result.get("bugs", []))
    score = result.get("overall_score", 0)
    rows = "".join(
        f"<tr><td>{e(str(b['line']))}</td><td class='{b['severity']}'>{SEVERITY_STYLE[b['severity']]['label']}</td>"
        f"<td>{e(SOURCE_LABELS.get(b.get('source'), str(b.get('source', ''))))}</td>"
        f"<td>{e(b['description'])}{'<br><em>Fix: ' + e(b['fix']) + '</em>' if b.get('fix') else ''}</td></tr>"
        for b in result.get("bugs", [])
    ) or "<tr><td colspan='4'>No issues found.</td></tr>"
    improvements = "".join(
        f"<li><strong>{e(i['title'])}</strong>: {e(i['detail'])}</li>" for i in result.get("improvements", []) or []
    ) or "<li>None provided.</li>"
    cx = ""
    if complexity:
        cx = (
            f"<p>{e(complexity['method'])} ({e(complexity['analysis_type'])}) - average complexity "
            f"<strong>{complexity['average_complexity']}</strong> (rank {e(str(complexity['rating']))}), "
            f"highest {complexity['max_complexity']}.</p>"
        )
        if complexity.get("maintainability_index") is not None:
            cx += f"<p>Maintainability index: <strong>{complexity['maintainability_index']}</strong> ({e(complexity['mi_label'])})</p>"
        if complexity.get("details"):
            cx += "<table><tr><th>Function</th><th>Line</th><th>Complexity</th><th>Rank</th></tr>" + "".join(
                f"<tr><td>{e(str(d['name']))}</td><td>{d['line']}</td><td>{d['complexity']}</td><td>{d['rank']}</td></tr>"
                for d in complexity["details"]
            ) + "</table>"
    improved = ""
    if result.get("improved_code"):
        improved = f"<h2>AI-improved code</h2><pre>{e(result['improved_code'])}</pre>"
    ai_note = (
        f"<p class='warning'>AI review was unavailable: {e(str(result.get('ai_error')))}</p>"
        if result.get("ai_status") == "failed" else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{APP_NAME} report</title>
<style>
body{{font-family:system-ui,Segoe UI,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#1b2140;line-height:1.5}}
h1{{margin-bottom:.2rem}} .meta{{color:#59618a}} table{{border-collapse:collapse;width:100%;margin:.5rem 0}}
th,td{{border:1px solid #d6dbf0;padding:.4rem .6rem;text-align:left;vertical-align:top}} th{{background:#eef1fb}}
pre{{background:#0e1330;color:#e7ebfa;padding:1rem;overflow:auto;border-radius:6px;font-size:.85rem}}
.critical{{color:#c62839;font-weight:600}} .warning{{color:#a86a00;font-weight:600}} .info{{color:#2556c4;font-weight:600}}
.score{{font-size:2.2rem;font-weight:700}}
</style></head><body>
<h1>{APP_NAME} - Code Review Report</h1>
<p class="meta">{e(language)} | generated {_stamp()}</p>
<p><span class="score">{score}/10</span> {e(score_label(score))} &nbsp;
Critical <strong>{counts['critical']}</strong> | Warnings <strong>{counts['warning']}</strong> | Info <strong>{counts['info']}</strong></p>
{ai_note}<h2>Summary</h2><p>{e(result.get('summary') or 'No summary.')}</p>
<h2>Issues</h2><table><tr><th>Line</th><th>Severity</th><th>Found by</th><th>Description</th></tr>{rows}</table>
<h2>Improvements</h2><ul>{improvements}</ul>
<h2>Complexity</h2>{cx}<p>{e(result.get('complexity_notes') or '')}</p>
<h2>Reviewed code</h2><pre>{e(code)}</pre>{improved}
</body></html>"""


def build_json(result, complexity, code, language) -> str:
    return json.dumps(
        {"app": APP_NAME, "generated": _stamp(), "language": language, "code": code,
         "review": result, "complexity": complexity},
        indent=2, ensure_ascii=False,
    )
