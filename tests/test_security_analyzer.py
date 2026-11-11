"""
TechSpecAnalyser — Security Analyzer & Secret Redactor Test Suite.
Tests CWE vulnerability pattern detection and secret masking guarantees.
"""
from analyzers.security_analyzer import SecurityAnalyzer
from core.security_redactor import redact_secrets


def test_sql_injection_detection():
    sec = SecurityAnalyzer()
    code = """
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
"""
    findings = sec.analyze(code, "Python", "db.py")
    assert any(f.get("cwe") == "CWE-89" for f in findings)


def test_command_injection_detection():
    sec = SecurityAnalyzer()
    code = """
import os
def ping_host(host):
    os.system("ping -c 1 " + host)
"""
    findings = sec.analyze(code, "Python", "net.py")
    assert any(f.get("cwe") == "CWE-78" for f in findings)


def test_unsafe_deserialization_pickle():
    sec = SecurityAnalyzer()
    code = """
import pickle
def load_data(raw_bytes):
    return pickle.loads(raw_bytes)
"""
    findings = sec.analyze(code, "Python", "data.py")
    assert any(f.get("cwe") == "CWE-502" for f in findings)


def test_xss_detection_react():
    sec = SecurityAnalyzer()
    code = """
function Component({ userHtml }) {
    return <div dangerouslySetInnerHTML={{ __html: userHtml }} />;
}
"""
    findings = sec.analyze(code, "JavaScript", "Component.jsx")
    assert any(f.get("cwe") == "CWE-79" for f in findings)


def test_weak_cryptography_md5():
    sec = SecurityAnalyzer()
    code = """
import hashlib
def hash_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()
"""
    findings = sec.analyze(code, "Python", "auth.py")
    assert any(f.get("cwe") == "CWE-327" for f in findings)


def test_disabled_ssl_verification():
    sec = SecurityAnalyzer()
    code = """
import requests
def fetch_api(url):
    return requests.get(url, verify=False)
"""
    findings = sec.analyze(code, "Python", "api_client.py")
    assert any(f.get("cwe") == "CWE-295" for f in findings)


def test_secret_redactor_masks_credentials():
    code_with_secrets = """
AWS_KEY = "AKIA1234567890ABCDEF"
GITHUB_PAT = "ghp_123456789012345678901234567890123456"
DB_URL = "postgres://admin:superSecretPassword123@db.example.com/prod"
"""
    redacted, secret_findings = redact_secrets(code_with_secrets)

    # Asserts that real secret values are completely purged from output
    assert "AKIA1234567890ABCDEF" not in redacted
    assert "ghp_123456789012345678901234567890123456" not in redacted
    assert "superSecretPassword123" not in redacted

    assert "[REDACTED_AWS_KEY]" in redacted
    assert "[REDACTED_GITHUB_TOKEN]" in redacted
    assert len(secret_findings) >= 2
