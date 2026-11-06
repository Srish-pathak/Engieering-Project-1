import os
import logging
import re
import time
from collections.abc import Callable
from typing import Any

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

try:
    from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
except ImportError:
    APIConnectionError = APIStatusError = APITimeoutError = OpenAI = None

from complexity import analyze_complexity
from local_checks import run_local_checks
from static_analysis import analyze_static
from syntax_checker import check_syntax
from utils import safe_json_parse

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
# "deepseek-chat" was retired by DeepSeek on 2026-07-24; V4 Flash is its replacement.
# Legacy names are mapped automatically so an old DEEPSEEK_MODEL setting keeps working.
LEGACY_MODEL_ALIASES = {"deepseek-chat": "deepseek-v4-flash", "deepseek-reasoner": "deepseek-v4-flash"}
_requested_model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash"
DEEPSEEK_MODEL_NAME = LEGACY_MODEL_ALIASES.get(_requested_model, _requested_model)
# JSON-only reviews should not spend tokens on (or be broken by) thinking mode.
DEEPSEEK_EXTRA_BODY = {"thinking": {"type": "disabled"}}

# Free alternatives. The provider is detected from the pasted key's prefix, so
# the sidebar box accepts a DeepSeek, Google Gemini or Groq key. Override the
# model with the AI_MODEL environment variable if a provider renames its models.
PROVIDERS = {
    "DeepSeek": {"base_url": DEEPSEEK_BASE_URL, "model": DEEPSEEK_MODEL_NAME, "extra_body": DEEPSEEK_EXTRA_BODY},
    "Gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.5-flash", "extra_body": None,
    },
    "Groq": {"base_url": "https://api.groq.com/openai/v1", "model": "openai/gpt-oss-120b", "extra_body": None},
}


def _clean_key(value: str) -> str:
    """Remove whitespace, wrapping quotes and a pasted 'Bearer ' prefix."""
    value = (value or "").strip().strip("\"'").strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    return value


def _resolve_key(api_key: str | None = None) -> str:
    return _clean_key(api_key or "") or _clean_key(os.getenv("DEEPSEEK_API_KEY") or "") or _clean_key(get_secret("DEEPSEEK_API_KEY") or "")


def detect_provider(api_key: str | None = None) -> str:
    """Pick the provider from the key format (DeepSeek is the default)."""
    key = _resolve_key(api_key)
    if key.startswith("AIza"):
        return "Gemini"
    if key.startswith("gsk_"):
        return "Groq"
    return "DeepSeek"


def provider_settings(api_key: str | None = None) -> dict[str, Any]:
    name = detect_provider(api_key)
    settings = dict(PROVIDERS[name])
    if name != "DeepSeek" and os.getenv("AI_MODEL"):
        settings["model"] = os.getenv("AI_MODEL", "").strip() or settings["model"]
    settings["name"] = name
    return settings

MAX_SOURCE_CHARACTERS = 40_000
LOGGER = logging.getLogger(__name__)


class MissingAIConfigurationError(EnvironmentError):
    """Raised when no DeepSeek API key is configured."""


def get_secret(name: str) -> str | None:
    """Read a named Streamlit secret without propagating missing-secrets errors."""
    try:
        value = st.secrets.get(name)
    except (KeyError, StreamlitSecretNotFoundError, AttributeError, FileNotFoundError):
        return None
    return value.strip() if isinstance(value, str) and value.strip() else None

SYSTEM_PROMPT = """
You are an experienced senior software engineer and security-focused code reviewer.

You ALWAYS respond with ONLY ONE VALID JSON OBJECT.
Never return markdown.
Analyze the complete source code before identifying any finding.
Report only evidence-based bugs, vulnerabilities, edge cases, performance issues,
maintainability problems, and practical improvements.
Do not invent line numbers, vulnerabilities, or problems that are unsupported by the code.
Explain every finding in beginner-friendly language and provide a technically correct fix.
For each issue in bugs or improvements, use the fields:
"title", "severity" (Critical/High/Medium/Low), "category", "file",
"line", "explanation", "why_it_matters", "suggested_solution", "corrected_code".

Schema:

{
  "summary":"",
  "bugs":[
    {
      "line":"",
      "severity":"",
      "description":""
    }
  ],
  "improvements":[
    {
      "title":"",
      "detail":""
    }
  ],
  "complexity_notes":"",
  "improved_code":"",
  "overall_score":8
}

Rules
- Return JSON only.
- improved_code should contain COMPLETE runnable code when a correction is useful.
- bugs may include security vulnerabilities only when evidence is present.
- Line numbers must refer to the supplied source. Use "N/A" when unavailable.
- Keep "overall_score" and "complexity_notes" transparent and evidence-based.
- Keep suggestions practical and educational.
- Don't invent bugs.
"""
def get_deepseek_client(api_key: str | None = None) -> Any:
    """Create an OpenAI-compatible client configured for DeepSeek.

    The key comes from, in order: the ``api_key`` argument (pasted in the UI and
    kept only in the user's session), the DEEPSEEK_API_KEY environment variable,
    or the DEEPSEEK_API_KEY Streamlit secret.
    """
    api_key = _resolve_key(api_key)
    if not api_key:
        raise MissingAIConfigurationError(
            "DEEPSEEK_API_KEY not found. Paste a key in the sidebar, set it as an "
            "environment variable, or add it to Streamlit secrets."
        )
    if OpenAI is None:
        raise ImportError("The openai package is required for DeepSeek reviews.")

    return OpenAI(
        api_key=api_key,
        base_url=provider_settings(api_key)["base_url"],
        timeout=60.0,
        max_retries=1,
    )


def candidate_keys(api_key: str | None = None) -> list[str]:
    """Every configured key in priority order: pasted, then Gemini, Groq, DeepSeek env/secrets."""
    ordered: list[str] = []
    for raw in (
        api_key,
        os.getenv("GEMINI_API_KEY"), get_secret("GEMINI_API_KEY"),
        os.getenv("GROQ_API_KEY"), get_secret("GROQ_API_KEY"),
        os.getenv("DEEPSEEK_API_KEY"), get_secret("DEEPSEEK_API_KEY"),
    ):
        key = _clean_key(raw or "")
        if key and key not in ordered:
            ordered.append(key)
    return ordered


def has_deepseek_key(api_key: str | None = None) -> bool:
    """True when any supported provider key is available (name kept for compatibility)."""
    return bool(candidate_keys(api_key))


def _safe_diagnostic(exc: Exception) -> str:
    """Return exception text with credentials and authorization headers removed."""
    text = "{}: {}".format(type(exc).__name__, exc)
    text = re.sub(r"(?i)(api[_ -]?key|authorization|bearer)\s*[:=]\s*[^\s,;]+", r"\1=<redacted>", text)
    text = re.sub(r"(?i)(bearer\s+)[^\s]+", r"\1<redacted>", text)
    text = re.sub(r"sk-[A-Za-z0-9_-]+", "<redacted>", text)
    return text[:500]


def _provider_error_message(exc: Exception, provider_name: str = "DeepSeek") -> tuple[str, str]:
    """Return a safe provider name, status, and message without exposing credentials."""
    text = "{} {}".format(type(exc).__name__, exc)
    lowered = text.lower()
    status_code = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    status = str(status_code or code or "")
    diagnostic = _safe_diagnostic(exc)
    LOGGER.warning("%s provider error: %s", provider_name, diagnostic)

    if isinstance(exc, MissingAIConfigurationError) or (
        ("api key" in lowered or "api_key" in lowered)
        and "not found" in lowered
    ):
        return (
            "{} API key is not configured. Paste it in the sidebar, set DEEPSEEK_API_KEY, "
            "or add it to Streamlit secrets. Offline analysis is still available.".format(provider_name),
            "missing_configuration",
        )

    if (
        "429" in text
        or status == "429"
        or "resource_exhausted" in lowered
        or "rate limit" in lowered
        or "quota" in lowered
    ):
        return (
            "{} rate limit or quota reached. Static analysis is still available.".format(provider_name),
            "rate_limited",
        )
    if "insufficient balance" in lowered or "credit balance is not enough" in lowered or status == "402":
        return (
            "{} account has insufficient balance. Top up your DeepSeek balance and try again.".format(provider_name),
            "insufficient_balance",
        )
    if "model" in lowered and any(k in lowered for k in ("not exist", "not found", "invalid model")):
        return (
            "{} model '{}' is not available. Set DEEPSEEK_MODEL (or AI_MODEL for Gemini/Groq) to a model your account can use.".format(
                provider_name, provider_settings().get("model")),
            "model_unavailable",
        )
    invalid_response = (
        ("empty" in lowered and "response" in lowered)
        or "incomplete response" in lowered
        or "could not parse model response" in lowered
    )
    if invalid_response:
        return (
            "{} returned an invalid or incomplete response. Static analysis is still available.".format(provider_name),
            "invalid_response",
        )
    if "invalid api key" in lowered:
        return (
            "The configured {} API key is invalid. Static analysis is still available.".format(provider_name),
            "invalid_api_key",
        )
    if (
        "401" in text
        or "403" in text
        or status in {"401", "403", "PERMISSION_DENIED"}
        or "permission_denied" in lowered
        or "authentication" in lowered
        or "incorrect api key" in lowered
    ):
        return (
            "{} access was denied. Check the API key and account permissions.".format(provider_name),
            "permission_denied",
        )
    is_timeout = (
        APITimeoutError is not None and isinstance(exc, APITimeoutError)
    ) or isinstance(exc, TimeoutError)
    if "timeout" in lowered or "timed out" in lowered or is_timeout:
        return (
            "{} timed out while generating the review. Static analysis is still available.".format(provider_name),
            "timeout",
        )
    is_connection_error = (
        APIConnectionError is not None
        and isinstance(exc, APIConnectionError)
    )
    if isinstance(exc, ConnectionError) or is_connection_error:
        return (
            "Could not connect to {}. Static analysis is still available.".format(provider_name),
            "network_error",
        )
    return (
        "{} review is currently unavailable. Static analysis is still available.".format(provider_name),
        "unavailable",
    )


# Anything except "no key at all" or "bad JSON" is worth retrying on the next provider.
FALLBACK_STATUSES = {
    "insufficient_balance", "invalid_api_key", "permission_denied", "rate_limited",
    "model_unavailable", "timeout", "network_error", "unavailable",
}


def _request(client: Any, settings: dict[str, Any], prompt: str) -> str:
    """One chat request with bounded retries on transient errors."""
    extra = {"extra_body": settings["extra_body"]} if settings["extra_body"] else {}
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=settings["model"],
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=4000,
                response_format={"type": "json_object"},
                **extra,
            )
            break
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            transient = status in {408, 409, 429, 500, 502, 503, 504}
            if not transient or attempt == 2:
                raise
            time.sleep(0.5 * (2 ** attempt))
    try:
        return response.choices[0].message.content or ""
    except (AttributeError, IndexError, TypeError):
        raise ValueError("The AI provider returned an empty or incomplete response.")


def _call_ai_with_provider(
    code: str, language: str, file_name: str = "<input>", api_key: str | None = None,
) -> tuple[str, str]:
    """Return (response text, provider name), falling back to the next configured key on failure."""
    prompt = build_user_prompt(code, language, file_name)
    keys: list[str | None] = list(candidate_keys(api_key)) or [None]
    for position, key in enumerate(keys):
        settings = provider_settings(key)
        try:
            client = get_deepseek_client(key)
            return _request(client, settings, prompt), settings["name"]
        except Exception as exc:
            try:
                exc._ai_provider = settings["name"]  # type: ignore[attr-defined]
            except Exception:
                pass
            _, status = _provider_error_message(exc, settings["name"])
            if status not in FALLBACK_STATUSES or position == len(keys) - 1:
                raise
    raise MissingAIConfigurationError("No AI key configured.")  # pragma: no cover


def _call_ai(code: str, language: str, file_name: str = "<input>", api_key: str | None = None) -> str:
    """Call the configured AI provider and return its response text."""
    return _call_ai_with_provider(code, language, file_name, api_key)[0]


def probe_deepseek_connectivity(api_key: str | None = None) -> dict[str, Any]:
    """Test every configured provider; connected if any one works. Returns non-secret status data."""
    first_failure = None
    for key in list(candidate_keys(api_key)) or [None]:
        outcome = _probe_one(key)
        if outcome["connected"]:
            return outcome
        first_failure = first_failure or outcome
    return first_failure


def _probe_one(api_key: str | None = None) -> dict[str, Any]:
    """Make a real, minimal request to one provider."""
    try:
        client = get_deepseek_client(api_key)
        settings = provider_settings(api_key)
        extra = {"extra_body": settings["extra_body"]} if settings["extra_body"] else {}
        response = client.chat.completions.create(
            model=settings["model"],
            messages=[
                {"role": "system", "content": "Return one valid JSON object only."},
                {"role": "user", "content": '{"status":"connected"}'},
            ],
            max_tokens=100,
            temperature=0,
            response_format={"type": "json_object"},
            **extra,
        )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("DeepSeek returned an empty connectivity response.")
        parsed = safe_json_parse(content)
        if parsed.get("error"):
            raise ValueError(parsed["summary"])
        return {
            "connected": True,
            "provider": settings["name"],
            "model": settings["model"],
            "base_url": settings["base_url"],
            "response": parsed,
        }
    except Exception as exc:
        LOGGER.warning("DeepSeek connectivity test failed: %s", _safe_diagnostic(exc))
        settings = provider_settings(api_key)
        error, status = _provider_error_message(exc, settings["name"])
        return {
            "connected": False,
            "provider": settings["name"],
            "model": settings["model"],
            "base_url": settings["base_url"],
            "status": status,
            "error": error,
        }


def build_user_prompt(code: str, language: str, file_name: str = "<input>") -> str:
    """Build the provider-neutral source-review prompt."""
    source = code
    if len(source) > MAX_SOURCE_CHARACTERS:
        source = (
            source[:MAX_SOURCE_CHARACTERS]
            + "\n\n[TRUNCATED: source exceeded the review input limit of 40,000 characters]"
        )
    return f"""
Review this {language} source file carefully.

File name: {file_name}

Code:

```{language.lower()}
{source}
```

Return your review strictly as the JSON schema described in your instructions."""


def review_code(
    code: str,
    language: str,
    file_name: str = "<input>",
    api_key: str | None = None,
) -> dict[str, Any]:
    """Run syntax, static, offline and DeepSeek review analysis for one code sample."""
    if not code or not code.strip():
        return {
            "bugs": [],
            "improvements": [],
            "complexity_notes": "N/A",
            "overall_score": 0,
            "improved_code": "",
            "summary": "No code was provided to review.",
            "error": True,
            "analysis_status": {"static": "failed", "ai": "not_run"},
        }

    syntax_result = check_syntax(code, language)
    if not syntax_result.get("valid", True):
        syntax_bugs = syntax_result.get("bugs", [])
        if isinstance(syntax_bugs, dict):
            syntax_bugs = [syntax_bugs]
        return {
            "summary": "Syntax error detected.",
            "bugs": syntax_bugs,
            "improvements": [],
            "complexity_notes": "Fix syntax errors before reviewing.",
            "improved_code": "",
            "overall_score": 1,
            "static_analysis": {"syntax": syntax_result, "findings": syntax_bugs},
            "analysis_status": {"static": "completed_with_errors", "ai": "not_run"},
        }

    static_bugs = sorted(
        analyze_static(code, language) + run_local_checks(code, language),
        key=lambda item: item["line"] if isinstance(item.get("line"), int) else 0,
    )
    complexity = analyze_complexity(code, language)

    # AI failures are kept separate from static analysis so deterministic
    # findings remain available even when DeepSeek is unavailable.
    try:
        response_text, used_provider = _call_ai_with_provider(code, language, file_name, api_key)
        if not response_text:
            raise ValueError("DeepSeek returned an empty or incomplete response.")
        ai_result = safe_json_parse(response_text)
        if ai_result.get("error"):
            raise ValueError(ai_result["summary"])
        _validate_ai_result(ai_result, file_name)
    except Exception as exc:
        message, ai_status = _provider_error_message(exc, getattr(exc, "_ai_provider", None) or detect_provider(api_key))
        return {
            "bugs": static_bugs,
            "improvements": [],
            "complexity_notes": "N/A",
            "overall_score": 0,
            "improved_code": "",
            "summary": "AI Review Unavailable — {}".format(message),
            "error": True,
            "static_analysis": {"syntax": syntax_result, "findings": static_bugs},
            "complexity": complexity,
            "analysis_status": {"static": "completed", "ai": ai_status},
            "ai_findings": [],
        }

    result = ai_result
    result["ai_findings"] = list(result.get("bugs", []))
    result["bugs"] = static_bugs + result.get("bugs", [])
    result["static_analysis"] = {"syntax": syntax_result, "findings": static_bugs}
    result["complexity"] = complexity
    result["analysis_status"] = {"static": "completed", "ai": "completed"}
    result["ai_provider"] = used_provider
    return result


def _validate_ai_result(result: dict[str, Any], file_name: str) -> None:
    """Validate provider-neutral review fields without changing the public schema."""
    required = {
        "summary",
        "bugs",
        "improvements",
        "complexity_notes",
        "improved_code",
        "overall_score",
    }
    missing = required.difference(result)
    if missing:
        raise ValueError("AI response is missing required fields: {}".format(", ".join(sorted(missing))))
    if not isinstance(result["summary"], str) or not isinstance(result["complexity_notes"], str):
        raise ValueError("AI response contains invalid text fields.")
    if not isinstance(result["bugs"], list) or not isinstance(result["improvements"], list):
        raise ValueError("AI response bugs and improvements must be arrays.")
    if not isinstance(result["improved_code"], str):
        raise ValueError("AI response improved_code must be text.")
    try:
        score = float(result["overall_score"])
    except (TypeError, ValueError) as exc:
        raise ValueError("AI response overall_score must be numeric.") from exc
    if not 0 <= score <= 10:
        raise ValueError("AI response overall_score must be between 0 and 10.")

    for finding in result["bugs"] + result["improvements"]:
        if not isinstance(finding, dict):
            raise ValueError("AI findings must be objects.")
        severity = finding.get("severity")
        if severity is not None:
            legacy_severity = str(severity).strip().lower()
            normalized = {
                "warning": "Medium",
                "info": "Low",
                "critical": "Critical",
                "high": "High",
                "medium": "Medium",
                "low": "Low",
            }.get(legacy_severity, legacy_severity.title())
            if normalized.lower() not in {
            "critical", "high", "medium", "low"
            }:
                raise ValueError("AI finding contains an invalid severity.")
            finding["severity"] = normalized
        finding.setdefault("file", file_name)
        finding.setdefault("line", "N/A")


def review_repo_files(
    files: list[dict[str, Any]],
    progress_callback: Callable[[int, int, str], None] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Review fetched files individually, reusing ``review_code`` for each.

    ``files`` is a sequence of dictionaries with path, language, and content.
    The optional callback receives (completed, total, current_path).
    """
    total = len(files)
    results = []
    score_values = []
    critical_count = 0
    warning_count = 0
    improvement_count = 0
    failed_count = 0
    ai_failed_count = 0

    for index, file_info in enumerate(files, start=1):
        path = file_info.get("path", "<unknown>")
        language = file_info.get("language", "")
        code = file_info.get("content", "")
        try:
            review = review_code(code, language, path, api_key)
            if not isinstance(review, dict):
                raise TypeError("The reviewer returned an invalid result.")
        except Exception as exc:
            review = {
                "summary": "Review failed: {}".format(exc),
                "bugs": [],
                "improvements": [],
                "complexity_notes": "Not available because the file review failed.",
                "overall_score": 0,
                "improved_code": "",
                "error": True,
                "analysis_status": {"static": "failed", "ai": "not_run"},
            }

        bugs = review.get("bugs", [])
        if isinstance(bugs, dict):
            bugs = [bugs]
        if not isinstance(bugs, list):
            bugs = []
        review["bugs"] = bugs

        complexity = None
        if language == "Python":
            try:
                complexity = analyze_complexity(code, language)
            except Exception as exc:
                complexity = {"error": "Complexity analysis failed: {}".format(exc)}

        for bug in bugs:
            severity = str(bug.get("severity", "info")).lower() if isinstance(bug, dict) else "info"
            if severity in {"critical", "high"}:
                critical_count += 1
            elif severity in {"warning", "medium"}:
                warning_count += 1
        improvements = review.get("improvements", [])
        if isinstance(improvements, list):
            improvement_count += len(improvements)

        is_error = bool(review.get("error"))
        if is_error:
            ai_status = review.get("analysis_status", {}).get("ai")
            if ai_status not in {None, "not_run"}:
                ai_failed_count += 1
            else:
                failed_count += 1
        else:
            try:
                score_values.append(float(review.get("overall_score", 0)))
            except (TypeError, ValueError):
                pass

        results.append({
            "path": path,
            "language": language,
            "content": code,
            "review": review,
            "complexity": complexity,
        })
        if progress_callback:
            progress_callback(index, total, path)

    return {
        "files_reviewed": len(results),
        "critical_bugs": critical_count,
        "warnings": warning_count,
        "improvement_count": improvement_count,
        "failed_files": failed_count,
        "ai_failed_files": ai_failed_count,
        "overall_score": round(sum(score_values) / len(score_values), 1) if score_values else None,
        "file_results": results,
    }
