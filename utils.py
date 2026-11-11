"""Shared helpers: language settings, JSON parsing, scoring, bug merging, review history."""
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

APP_NAME = "TechSpecAnalyser"

LANGUAGE_CONFIG = {
    "Python": {"ace_mode": "python", "ext": ".py", "supports_radon": True},
    "C++": {"ace_mode": "c_cpp", "ext": ".cpp", "supports_radon": False},
    "Java": {"ace_mode": "java", "ext": ".java", "supports_radon": False},
}

SEVERITY_ORDER = ["critical", "warning", "info"]
SEVERITY_STYLE = {
    "critical": {"emoji": "🔴", "label": "Critical", "color": "#FF6B7A"},
    "warning": {"emoji": "🟡", "label": "Warning", "color": "#FFC857"},
    "info": {"emoji": "🔵", "label": "Info", "color": "#7AA7FF"},
}
SEVERITY_ALIASES = {
    "error": "critical", "high": "critical", "major": "critical", "severe": "critical", "blocker": "critical",
    "medium": "warning", "moderate": "warning", "warn": "warning",
    "low": "info", "minor": "info", "suggestion": "info", "note": "info", "style": "info",
}
SOURCE_LABELS = {"syntax": "Syntax check", "g++": "g++ compiler", "static": "Static analysis", "ai": "AI review"}


# ------------------------------------------------------------ JSON parsing
def safe_json_parse(raw_text) -> dict:
    """Turn the model's text into a dict. Never raises; returns an error dict instead."""
    if not raw_text or not str(raw_text).strip():
        return _fallback_response("Empty response from model.")

    cleaned = str(raw_text).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)  # strip markdown fences if present
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)  # isolate the outermost {...}
    if match:
        cleaned = match.group(0)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return _fallback_response(f"Could not parse model response: {e}")
    if not isinstance(data, dict):
        return _fallback_response("Model returned JSON, but not a JSON object.")
    return _normalize_response(data)


def _normalize_response(data: dict) -> dict:
    """Make sure every expected key exists with the right type, so the UI never KeyErrors."""
    data["summary"] = str(data.get("summary") or "")
    data["complexity_notes"] = str(data.get("complexity_notes") or "No complexity notes provided.")
    data["improved_code"] = str(data.get("improved_code") or "")
    data["bugs"] = [normalize_bug(b, "ai") for b in (data.get("bugs") or []) if isinstance(b, dict)]
    data["improvements"] = [
        {"title": str(i.get("title") or "Suggestion"), "detail": str(i.get("detail") or "")}
        for i in (data.get("improvements") or []) if isinstance(i, dict)
    ]
    try:
        data["overall_score"] = max(1.0, min(10.0, float(data.get("overall_score", 5))))
    except (TypeError, ValueError):
        data["overall_score"] = 5.0
    return data


def _fallback_response(error_message: str) -> dict:
    return {
        "bugs": [], "improvements": [], "complexity_notes": "N/A", "overall_score": 0,
        "improved_code": "", "summary": error_message, "error": True,
    }


# ------------------------------------------------------------ bugs
def normalize_bug(bug: dict, default_source="static") -> dict:
    severity = str(bug.get("severity", "info")).strip().lower()
    severity = SEVERITY_ALIASES.get(severity, severity)
    if severity not in SEVERITY_STYLE:
        severity = "info"
    line = bug.get("line", "N/A")
    return {
        "line": line if line not in (None, "") else "N/A",
        "severity": severity,
        "description": str(bug.get("description") or "No description provided."),
        "fix": str(bug.get("fix") or ""),
        "source": bug.get("source") or default_source,
        "rule": bug.get("rule", ""),
    }


def _line_number(bug):
    m = re.search(r"\d+", str(bug.get("line", "")))
    return int(m.group()) if m else 10**6


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "not", "are", "was", "will", "has", "have", "can", "may",
    "use", "used", "using", "code", "line", "is", "it", "in", "on", "of", "to", "be", "an", "or", "so", "at",
    "by", "as", "if", "its", "but", "when", "which", "instead", "should", "does", "did",
}


def _words(text):
    """Meaningful lowercase words of a description (no stop-words, no single letters)."""
    return {w for w in re.findall(r"[a-z0-9_]+", text.lower()) if len(w) > 1 and w not in STOPWORDS}


def _same_issue(a: str, b: str) -> bool:
    """Two descriptions on the same line are one issue if they share enough meaningful words."""
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return False
    shared = len(wa & wb)
    return shared >= 2 or shared / len(wa | wb) >= 0.4


def merge_bugs(local_bugs, ai_bugs):
    """Combine local and AI findings, drop near-duplicates, sort by severity then line."""
    merged = [normalize_bug(b, b.get("source", "static")) for b in local_bugs]
    for bug in (normalize_bug(b, "ai") for b in ai_bugs):
        duplicate = any(
            str(existing["line"]) == str(bug["line"]) and _same_issue(existing["description"], bug["description"])
            for existing in merged
        )
        if not duplicate:
            merged.append(bug)
    merged.sort(key=lambda b: (SEVERITY_ORDER.index(b["severity"]), _line_number(b)))
    return merged


def count_by_severity(bugs):
    counts = {s: 0 for s in SEVERITY_ORDER}
    for bug in bugs:
        counts[bug.get("severity", "info")] = counts.get(bug.get("severity", "info"), 0) + 1
    return counts


# ------------------------------------------------------------ scoring
def compute_quality_score(bugs, complexity, ai_score=None):
    """
    Transparent score out of 10 (easy to explain in a viva).

    rule_score = 10 - penalties
        critical bug  : -2.0 each (max -6)
        warning       : -1.0 each (max -3)
        info          : -0.25 each (max -1)
        worst function complexity: A 0, B -0.5, C -1.5, D -2.5, E/F -3.5
                                   (halved when complexity is only estimated)
        maintainability index    : rank B -0.75, rank C -1.5  (Python only)
    final = 60% rule_score + 40% AI opinion (when the AI review is available)
    """
    counts = count_by_severity(bugs)
    penalties = []

    def add(label, points):
        if points > 0:
            penalties.append({"label": label, "points": round(points, 2)})

    add(f"{counts['critical']} critical bug(s)", min(6.0, 2.0 * counts["critical"]))
    add(f"{counts['warning']} warning(s)", min(3.0, 1.0 * counts["warning"]))
    add(f"{counts['info']} info note(s)", min(1.0, 0.25 * counts["info"]))

    if complexity and not complexity.get("error"):
        table = {"A": 0, "B": 0.5, "C": 1.5, "D": 2.5, "E": 3.5, "F": 3.5}
        worst = _rank_for(complexity.get("max_complexity", 1))
        points = table[worst]
        if complexity.get("analysis_type") == "estimated":
            points /= 2
        add(f"highest function complexity (rank {worst})", points)
        add("low maintainability index", {"B": 0.75, "C": 1.5}.get(complexity.get("mi_rank"), 0))

    rule_score = max(1.0, 10.0 - sum(p["points"] for p in penalties))
    if ai_score is None:
        final = rule_score
    else:
        final = 0.6 * rule_score + 0.4 * max(1.0, min(10.0, float(ai_score)))
    return {
        "score": round(max(1.0, min(10.0, final)), 1),
        "rule_score": round(rule_score, 1),
        "ai_score": None if ai_score is None else round(float(ai_score), 1),
        "penalties": penalties,
    }


def _rank_for(value):
    for limit, letter in ((5, "A"), (10, "B"), (20, "C"), (30, "D"), (40, "E")):
        if value <= limit:
            return letter
    return "F"


def score_band(score: float):
    """One place defines label + colour, so they can never disagree."""
    if score >= 8.5:
        return "Excellent", "green"
    if score >= 7:
        return "Good", "green"
    if score >= 5:
        return "Needs Work", "orange"
    return "Poor", "red"


def score_color(score: float) -> str:
    return score_band(score)[1]


def score_label(score: float) -> str:
    return score_band(score)[0]


# ------------------------------------------------------------ text formatting
def format_bug_entry(bug: dict) -> str:
    """Render a single bug dict into a readable markdown string."""
    style = SEVERITY_STYLE.get(str(bug.get("severity", "info")).lower(), SEVERITY_STYLE["info"])
    line = bug.get("line", "N/A")
    desc = bug.get("description", "No description provided.")
    text = f"{style['emoji']} **{style['label']}** (Line {line}): {desc}"
    if bug.get("fix"):
        text += f"\n\n   Fix: {bug['fix']}"
    return text


def format_improvement_entry(item: dict) -> str:
    return f"💡 **{item.get('title', 'Suggestion')}**\n\n{item.get('detail', '')}"


# ------------------------------------------------------------ review history
HISTORY_FILE = Path(os.getenv("TECSPACE_HISTORY_FILE", Path(__file__).with_name("review_history.json")))
HISTORY_LIMIT = 25


def history_enabled() -> bool:
    """Set TECSPACE_SAVE_HISTORY=0 on shared/public deployments to keep history out of the disk."""
    return os.getenv("TECSPACE_SAVE_HISTORY", "1") != "0"


def load_history() -> list:
    if not history_enabled() or not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []  # a corrupted history file must never crash the app


def _write_history(entries):
    if not history_enabled():
        return
    try:
        fd, tmp = tempfile.mkstemp(dir=HISTORY_FILE.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=1)
        os.replace(tmp, HISTORY_FILE)  # atomic: never leaves a half-written file
    except OSError:
        pass


def make_history_entry(language, code, result, complexity) -> dict:
    counts = count_by_severity(result.get("bugs", []))
    return {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "time": datetime.now().strftime("%d %b %Y, %H:%M"),
        "language": language,
        "score": result.get("overall_score", 0),
        "critical": counts["critical"], "warning": counts["warning"], "info": counts["info"],
        "summary": (result.get("summary") or "")[:160],
        "code": code,
        "result": result,
        "complexity": complexity,
    }


def add_history(entries: list, entry: dict) -> list:
    entries = ([entry] + list(entries))[:HISTORY_LIMIT]
    _write_history(entries)
    return entries


def clear_history() -> list:
    _write_history([])
    return []
