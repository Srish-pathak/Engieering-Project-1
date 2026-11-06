"""Shared constants and JSON helpers."""

import json
import re

LANGUAGE_CONFIG = {
    "Python": {"ace_mode": "python", "ext": ".py", "supports_radon": True},
    "C++": {"ace_mode": "c_cpp", "ext": ".cpp", "supports_radon": False},
    "Java": {"ace_mode": "java", "ext": ".java", "supports_radon": False},
    "JavaScript": {"ace_mode": "javascript", "ext": ".js", "supports_radon": False},
    "JSX": {"ace_mode": "jsx", "ext": ".jsx", "supports_radon": False},
    "TypeScript": {"ace_mode": "typescript", "ext": ".ts", "supports_radon": False},
    "TSX": {"ace_mode": "tsx", "ext": ".tsx", "supports_radon": False},
    "HTML": {"ace_mode": "html", "ext": ".html", "supports_radon": False},
    "CSS": {"ace_mode": "css", "ext": ".css", "supports_radon": False},
    "SCSS": {"ace_mode": "scss", "ext": ".scss", "supports_radon": False},
}

SEVERITY_STYLE = {
    "critical": {"emoji": "🔴", "label": "Critical"},
    "high": {"emoji": "🟠", "label": "High"},
    "warning": {"emoji": "🟡", "label": "Warning"},
    "medium": {"emoji": "🟡", "label": "Medium"},
    "low": {"emoji": "🔵", "label": "Low"},
    "info": {"emoji": "🔵", "label": "Info"},
}
SEVERITY_ORDER = {"critical": 0, "high": 1, "warning": 2, "medium": 3, "low": 4, "info": 5}


def safe_json_parse(raw_text: str) -> dict:
    """Parse a model reply into the review schema, tolerating code fences and chatter."""
    if not raw_text:
        return _fallback_response("Empty response from model.")

    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:[A-Za-z0-9_-]+)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return _normalize_response(data)
        error = "Model response JSON must be an object."
    except json.JSONDecodeError as exc:
        error = str(exc)

    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character != "{":
            continue
        try:
            data, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return _normalize_response(data)
    return _fallback_response("Could not parse model response: {}".format(error))


def _normalize_response(data: dict) -> dict:
    """Make sure every expected key exists so the UI never hits a KeyError."""
    data.setdefault("summary", "")
    data.setdefault("complexity_notes", "No complexity notes provided.")
    data.setdefault("improved_code", "")
    for key in ("bugs", "improvements"):
        if not isinstance(data.get(key), list):
            data[key] = []
    try:
        score = float(data.get("overall_score", 5))
        if score != score:
            raise ValueError
        data["overall_score"] = max(0.0, min(10.0, score))
    except (TypeError, ValueError):
        data["overall_score"] = 5.0
    return data


def _fallback_response(message: str) -> dict:
    return {
        "bugs": [], "improvements": [], "complexity_notes": "N/A", "overall_score": 0,
        "improved_code": "", "summary": message, "error": True,
    }


def score_color(score: float) -> str:
    return "green" if score >= 8 else "orange" if score >= 5 else "red"


def score_label(score: float) -> str:
    if score >= 8:
        return "Excellent"
    if score >= 6:
        return "Good"
    if score >= 4:
        return "Needs Work"
    return "Poor"


def severity_key(item: dict) -> str:
    return str(item.get("severity", "info")).strip().lower()


def sort_findings(items: list) -> list:
    return sorted(
        (i for i in items if isinstance(i, dict)),
        key=lambda b: SEVERITY_ORDER.get(severity_key(b), 5),
    )


def format_bug_entry(bug: dict) -> str:
    style = SEVERITY_STYLE.get(severity_key(bug), SEVERITY_STYLE["info"])
    text = bug.get("description") or bug.get("explanation") or bug.get("title") or "No description provided."
    return "{} **{}** (line {}): {}".format(style["emoji"], style["label"], bug.get("line", "N/A"), text)


def format_improvement_entry(item: dict) -> str:
    detail = item.get("detail") or item.get("explanation") or ""
    return "💡 **{}**\n\n{}".format(item.get("title", "Suggestion"), detail)
