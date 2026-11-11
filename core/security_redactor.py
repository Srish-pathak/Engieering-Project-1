"""
TechSpecAnalyser — Security Redactor Engine.
Detects and redacts sensitive credentials, tokens, and API secrets before
logging, transmitting to Google Gemini, or displaying in public reports.
"""
import re
from typing import Any, Dict, List, Tuple

# Compiled secret patterns
SECRET_PATTERNS = [
    {
        "name": "AWS Access Key",
        "pattern": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "placeholder": "[REDACTED_AWS_KEY]",
        "cwe": "CWE-798",
        "severity": "critical",
    },
    {
        "name": "GitHub Personal Access Token",
        "pattern": re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b"),
        "placeholder": "[REDACTED_GITHUB_TOKEN]",
        "cwe": "CWE-798",
        "severity": "critical",
    },
    {
        "name": "Generic Private Key",
        "pattern": re.compile(
            r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP|PRIVATE) KEY[^\r\n]*-----[\s\S]*?-----END (?:RSA|EC|DSA|OPENSSH|PGP|PRIVATE) KEY-----"
        ),
        "placeholder": "[REDACTED_PRIVATE_KEY]",
        "cwe": "CWE-312",
        "severity": "critical",
    },
    {
        "name": "JSON Web Token (JWT)",
        "pattern": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,}\.[A-Za-z0-9._-]{10,}\b"),
        "placeholder": "[REDACTED_JWT_TOKEN]",
        "cwe": "CWE-798",
        "severity": "warning",
    },
    {
        "name": "Slack Token",
        "pattern": re.compile(r"\bxox[baprs]-[0-9a-zA-Z]{10,48}\b"),
        "placeholder": "[REDACTED_SLACK_TOKEN]",
        "cwe": "CWE-798",
        "severity": "critical",
    },
    {
        "name": "Database Connection URL with Credentials",
        "pattern": re.compile(
            r"(?:postgres|postgresql|mysql|mongodb|redis):\/\/[^:\s]+:[^@\s]+@[^\s\/]+"
        ),
        "placeholder": "[REDACTED_DB_CONNECTION_STRING]",
        "cwe": "CWE-312",
        "severity": "critical",
    },
    {
        "name": "Hardcoded API Key / Secret Variable",
        "pattern": re.compile(
            r"""(?i)\b(api_key|apikey|secret_key|client_secret|access_token|auth_token)\s*=\s*['"]([A-Za-z0-9_\-\.]{16,})['"]"""
        ),
        "placeholder": r'\1="[REDACTED_SECRET]"',
        "is_group_replacement": True,
        "cwe": "CWE-798",
        "severity": "critical",
    },
    {
        "name": "Hardcoded Password Assignment",
        "pattern": re.compile(
            r"""(?i)\b(password|passwd|pwd)\s*=\s*['"]([^'"]{6,})['"]"""
        ),
        "placeholder": r'\1="[REDACTED_PASSWORD]"',
        "is_group_replacement": True,
        "cwe": "CWE-798",
        "severity": "critical",
    },
]


def redact_secrets(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Scans text for secrets, masks them, and returns (redacted_text, detected_secrets).
    Never stores or returns actual secret plaintexts.
    """
    if not text:
        return text, []

    redacted_text = text
    findings: List[Dict[str, Any]] = []

    lines = text.splitlines()

    for pattern_info in SECRET_PATTERNS:
        name = pattern_info["name"]
        pat = pattern_info["pattern"]
        placeholder = pattern_info["placeholder"]
        cwe = pattern_info["cwe"]
        severity = pattern_info["severity"]
        is_group = pattern_info.get("is_group_replacement", False)

        for match in pat.finditer(text):
            # Calculate line number
            start_pos = match.start()
            line_no = text[:start_pos].count("\n") + 1
            line_content = lines[line_no - 1] if line_no <= len(lines) else ""

            # Sanitized evidence snippet (never show secret value)
            findings.append({
                "rule": "hardcoded-secret",
                "cwe": cwe,
                "severity": severity,
                "title": f"Exposed {name}",
                "description": f"Potential hardcoded secret or credential detected ({name}). Secrets should be loaded from environment variables or a secrets manager.",
                "line": line_no,
                "snippet": line_content[:120],
                "source": "static-security",
                "confidence": "high",
            })

        if is_group:
            redacted_text = pat.sub(placeholder, redacted_text)
        else:
            redacted_text = pat.sub(placeholder, redacted_text)

    return redacted_text, findings


def mask_token(token: str) -> str:
    """Mask a token for UI display e.g. ghp_1234...abcd"""
    if not token:
        return ""
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"
