"""Code review orchestration: syntax -> static/offline checks -> Gemini -> merged result."""

import os
import re
import time
from collections.abc import Callable
from typing import Any

from complexity import analyze_complexity
from local_checks import run_local_checks
from static_analysis import analyze_static
from syntax_checker import check_syntax
from utils import safe_json_parse, severity_key

try:  # keep the project importable (and testable) without these installed
    import streamlit as st
except ImportError:
    st = None
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_MODEL = "gemini-2.5-flash"
MAX_SOURCE_CHARACTERS = 40_000
MAX_RETRY_WAIT_SECONDS = 30

SYSTEM_PROMPT = """
You are a senior software engineer performing a code review.

You ALWAYS respond with ONLY ONE VALID JSON OBJECT.
Never return markdown. Never wrap the JSON in code fences. Never explain anything outside the JSON.

Schema:

{
  "summary": "",
  "bugs": [{"line": "", "severity": "", "description": ""}],
  "improvements": [{"title": "", "detail": ""}],
  "complexity_notes": "",
  "improved_code": "",
  "overall_score": 8
}

Rules
- Return JSON only.
- severity must be one of: Critical, High, Medium, Low.
- line is the line number in the supplied source, or "N/A".
- improved_code should contain the COMPLETE corrected file when a correction is useful, otherwise "".
- Report only problems supported by the code. Do not invent bugs.
- overall_score is 0-10 and must be justified by your findings.
- Keep suggestions practical and educational.
"""


class MissingKeyError(EnvironmentError):
    """No Gemini API key is configured."""


def _secret(name: str) -> str | None:
    if st is None:
        return None
    try:
        value = st.secrets.get(name)
    except Exception:
        return None
    return value.strip() if isinstance(value, str) and value.strip() else None


def clean_key(value: str | None) -> str:
    """Strip whitespace, wrapping quotes and a pasted 'Bearer ' prefix."""
    value = (value or "").strip().strip("\"'").strip()
    return value[7:].strip() if value.lower().startswith("bearer ") else value


def resolve_key(api_key: str | None = None) -> str:
    """Order: key passed in (sidebar) -> GEMINI_API_KEY env/.env -> Streamlit secret."""
    for candidate in (api_key, os.getenv("GEMINI_API_KEY"), os.getenv("GOOGLE_API_KEY"), _secret("GEMINI_API_KEY")):
        key = clean_key(candidate)
        if key:
            return key
    return ""


def has_key(api_key: str | None = None) -> bool:
    return bool(resolve_key(api_key))


def resolve_model(model: str | None = None) -> str:
    return (model or "").strip() or os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL


def get_client(api_key: str | None = None) -> Any:
    key = resolve_key(api_key)
    if not key:
        raise MissingKeyError(
            "GEMINI_API_KEY not found. Paste a key in the sidebar or set it in .env / the environment."
        )
    from google import genai  # imported lazily so the rest of the app works without it
    return genai.Client(api_key=key)


# ------------------------------------------------------------------ error handling
def classify_error(exc: Exception) -> tuple[str, str]:
    """Map an exception to (status, friendly message). Never includes the key."""
    text = "{} {}".format(type(exc).__name__, exc)
    low = text.lower()
    code = str(getattr(exc, "code", "") or getattr(exc, "status_code", ""))

    if isinstance(exc, MissingKeyError):
        return "missing_key", "No Gemini API key. Paste one in the sidebar (free at aistudio.google.com/apikey)."
    if "api key not valid" in low or "api_key_invalid" in low or "invalid api key" in low:
        return "invalid_api_key", "Gemini says the API key is invalid. Create a new key and paste it again."
    if code == "429" or "429" in low or "resource_exhausted" in low or "quota" in low or "rate limit" in low:
        return "rate_limited", "Gemini rate limit or free-tier quota reached. Wait a minute, or review fewer files."
    if code == "403" or "permission_denied" in low or "403" in low:
        return "permission_denied", "Gemini denied access. Check the key and that the Gemini API is enabled for it."
    if code == "404" or "not found" in low or "is not supported" in low:
        return "model_unavailable", "That Gemini model is not available. Change the model name in the sidebar (e.g. gemini-2.5-flash)."
    if "timed out" in low or "timeout" in low or isinstance(exc, TimeoutError):
        return "timeout", "Gemini timed out. Try again."
    if "connect" in low or isinstance(exc, ConnectionError):
        return "network_error", "Could not reach Gemini. Check your internet connection."
    if "empty" in low or "could not parse" in low or "invalid response" in low:
        return "invalid_response", "Gemini returned an unusable response. Try again."
    return "unavailable", "Gemini review failed: {}".format(str(exc)[:200])


def _retry_delay(exc: Exception) -> float | None:
    """Seconds Gemini asks us to wait on a 429, if it says so."""
    match = re.search(r"retry(?:Delay)?\D{0,12}(\d+(?:\.\d+)?)\s*s", str(exc), re.IGNORECASE)
    return float(match.group(1)) if match else None


# ------------------------------------------------------------------ AI call
def build_user_prompt(code: str, language: str, file_name: str = "<input>") -> str:
    source = code
    if len(source) > MAX_SOURCE_CHARACTERS:
        source = source[:MAX_SOURCE_CHARACTERS] + "\n\n[TRUNCATED: input limit of 40,000 characters]"
    return (
        "Review this {lang} source file.\n\nFile name: {name}\n\nCode:\n\n```{fence}\n{src}\n```\n\n"
        "Return your review strictly as the JSON schema described in your instructions."
    ).format(lang=language, name=file_name, fence=language.lower(), src=source)


def _generate(client: Any, model: str, prompt: str, system: str | None, max_tokens: int) -> str:
    config: dict[str, Any] = {
        "temperature": 0.2,
        "response_mime_type": "application/json",
        "max_output_tokens": max_tokens,
    }
    if system:
        config["system_instruction"] = system
    response = client.models.generate_content(model=model, contents=prompt, config=config)
    return getattr(response, "text", None) or ""


def _call_ai(code: str, language: str, file_name: str, api_key: str | None, model: str | None) -> str:
    client = get_client(api_key)
    name = resolve_model(model)
    prompt = build_user_prompt(code, language, file_name)
    for attempt in range(2):
        try:
            return _generate(client, name, prompt, SYSTEM_PROMPT, 8192)
        except Exception as exc:
            status, _ = classify_error(exc)
            wait = _retry_delay(exc)
            if status != "rate_limited" or attempt == 1 or wait is None or wait > MAX_RETRY_WAIT_SECONDS:
                raise
            time.sleep(wait + 1)
    return ""


def probe_connection(api_key: str | None = None, model: str | None = None) -> dict[str, Any]:
    """Tiny real request to confirm the key and model work."""
    name = resolve_model(model)
    try:
        client = get_client(api_key)
        text = _generate(client, name, 'Return {"status":"connected"} as JSON.', None, 50)
        if not text.strip():
            raise ValueError("empty response")
        return {"connected": True, "model": name}
    except Exception as exc:
        status, message = classify_error(exc)
        return {"connected": False, "model": name, "status": status, "error": message}


# ------------------------------------------------------------------ validation
def _validate_ai_result(result: dict[str, Any], file_name: str) -> None:
    levels = {"warning": "Medium", "info": "Low", "critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
    for finding in result["bugs"] + result["improvements"]:
        if not isinstance(finding, dict):
            raise ValueError("invalid response: findings must be objects")
        if "severity" in finding:
            finding["severity"] = levels.get(str(finding["severity"]).strip().lower(), "Low")
        finding.setdefault("file", file_name)
        finding.setdefault("line", "N/A")
    if not isinstance(result.get("improved_code", ""), str):
        result["improved_code"] = ""


# ------------------------------------------------------------------ public API
def review_code(
    code: str,
    language: str,
    file_name: str = "<input>",
    api_key: str | None = None,
    model: str | None = None,
    use_ai: bool = True,
) -> dict[str, Any]:
    """Review one source file. Offline findings always survive an AI failure."""
    if not code or not code.strip():
        return {
            "summary": "No code was provided to review.", "bugs": [], "improvements": [],
            "complexity_notes": "N/A", "improved_code": "", "overall_score": None, "error": True,
            "analysis_status": {"static": "failed", "ai": "not_run"},
        }

    syntax = check_syntax(code, language)
    if not syntax["valid"]:
        return {
            "summary": "Syntax error detected.", "bugs": syntax["bugs"], "improvements": [],
            "complexity_notes": "Fix syntax errors before reviewing.", "improved_code": "",
            "overall_score": 1, "complexity": None,
            "analysis_status": {"static": "completed_with_errors", "ai": "not_run"},
        }

    offline = sorted(
        analyze_static(code, language) + run_local_checks(code, language),
        key=lambda b: b["line"] if isinstance(b.get("line"), int) else 0,
    )
    base = {
        "bugs": offline, "improvements": [], "complexity_notes": "", "improved_code": "",
        "overall_score": None, "complexity": analyze_complexity(code, language),
    }

    if not use_ai:
        base["summary"] = "Offline checks only (AI review skipped)."
        base["analysis_status"] = {"static": "completed", "ai": "skipped"}
        return base

    try:
        text = _call_ai(code, language, file_name, api_key, model)
        parsed = safe_json_parse(text)
        if parsed.get("error"):
            raise ValueError(parsed["summary"])
        _validate_ai_result(parsed, file_name)
    except Exception as exc:
        status, message = classify_error(exc)
        base["summary"] = "AI review unavailable. {} Offline checks are shown.".format(message)
        base["ai_error"] = message
        base["analysis_status"] = {"static": "completed", "ai": status}
        return base

    parsed["ai_findings"] = list(parsed["bugs"])
    parsed["bugs"] = offline + parsed["bugs"]
    parsed["complexity"] = base["complexity"]
    parsed["analysis_status"] = {"static": "completed", "ai": "completed"}
    return parsed


# Statuses after which every further file would fail the same way.
_STOP_AI_STATUSES = {"missing_key", "invalid_api_key", "permission_denied", "model_unavailable", "rate_limited"}


def review_repo_files(
    files: list[dict[str, Any]],
    progress_callback: Callable[[int, int, str], None] | None = None,
    api_key: str | None = None,
    model: str | None = None,
    use_ai: bool = True,
    delay_seconds: float = 1.0,
) -> dict[str, Any]:
    """Review fetched files one by one. A failure in one file never stops the rest."""
    total = len(files)
    results, scores = [], []
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    ai_ok = ai_failed = 0
    ai_active = use_ai
    ai_stopped_reason = None

    for index, info in enumerate(files, start=1):
        path, language, code = info.get("path", "<unknown>"), info.get("language", ""), info.get("content", "")
        try:
            review = review_code(code, language, path, api_key, model, use_ai=ai_active)
        except Exception as exc:  # defensive: never let one file kill the run
            review = {"summary": "Review failed: {}".format(exc), "bugs": [], "improvements": [],
                      "overall_score": None, "improved_code": "", "error": True,
                      "analysis_status": {"static": "failed", "ai": "not_run"}}

        for bug in review.get("bugs", []):
            if isinstance(bug, dict):
                level = severity_key(bug)
                level = {"warning": "medium", "info": "low"}.get(level, level)
                counts[level if level in counts else "low"] += 1

        status = review.get("analysis_status", {}).get("ai")
        if status == "completed":
            ai_ok += 1
            if isinstance(review.get("overall_score"), (int, float)):
                scores.append(float(review["overall_score"]))
        elif ai_active and status not in (None, "not_run", "skipped"):
            ai_failed += 1
            if status in _STOP_AI_STATUSES:
                ai_active = False
                ai_stopped_reason = review.get("ai_error") or status
        results.append({"path": path, "language": language, "content": code, "review": review})

        if progress_callback:
            progress_callback(index, total, path)
        if ai_active and delay_seconds and index < total:
            time.sleep(delay_seconds)

    return {
        "files_reviewed": len(results),
        "severity_counts": counts,
        "total_findings": sum(counts.values()),
        "ai_reviewed_files": ai_ok,
        "ai_failed_files": ai_failed,
        "ai_stopped_reason": ai_stopped_reason,
        "overall_score": round(sum(scores) / len(scores), 1) if scores else None,
        "file_results": results,
    }
