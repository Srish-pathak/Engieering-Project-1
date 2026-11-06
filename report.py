"""Markdown / JSON report builders."""

import json
from datetime import datetime
from typing import Any

from utils import format_bug_entry, format_improvement_entry, sort_findings


def build_markdown_report(result: dict[str, Any], language: str, source: str) -> str:
    score = result.get("overall_score")
    lines = [
        "# AI Code Review Report", "", "_Generated {}_".format(datetime.now().strftime("%Y-%m-%d %H:%M")), "",
        "- Language: {}".format(language),
        "- Score: {}".format("{}/10".format(score) if score is not None else "n/a (AI review not completed)"),
        "", "## Summary", "", result.get("summary") or "No summary.", "", "## Findings", "",
    ]
    lines += ["- " + format_bug_entry(b) for b in sort_findings(result.get("bugs", []))] or ["No findings."]
    lines += ["", "## Improvements", ""]
    lines += [format_improvement_entry(i) + "\n" for i in result.get("improvements", []) if isinstance(i, dict)] or ["None."]
    lines += ["", "## Source", "", "```{}".format(language.lower()), source, "```"]
    if result.get("improved_code"):
        lines += ["", "## AI-improved code", "", "```{}".format(language.lower()), result["improved_code"], "```"]
    return "\n".join(lines) + "\n"


def build_json_report(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2, default=str)


def build_repo_markdown(repo: dict[str, Any], review: dict[str, Any]) -> str:
    counts = review["severity_counts"]
    score = review["overall_score"]
    lines = [
        "# Repository Report: {}".format(repo["full_name"]), "",
        "- Branch: {}".format(repo["branch"]),
        "- Files reviewed: {}".format(review["files_reviewed"]),
        "- Findings: {} critical, {} high, {} medium, {} low".format(
            counts["critical"], counts["high"], counts["medium"], counts["low"]),
        "- Average AI score: {}".format("{}/10".format(score) if score is not None else "n/a"),
        "",
    ]
    for item in review["file_results"]:
        r = item["review"]
        lines += ["## {}".format(item["path"]), "", r.get("summary") or "No summary.", ""]
        lines += ["- " + format_bug_entry(b) for b in sort_findings(r.get("bugs", []))] or ["No findings."]
        lines.append("")
    return "\n".join(lines)
