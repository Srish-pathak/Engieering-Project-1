"""
TechSpecAnalyser — Google Gemini AI Engine Test Suite.
Tests client configuration, mock generation, rate limit handling, and quota circuit breaker.
"""
from unittest.mock import MagicMock
from google.genai import errors as genai_errors

from core.gemini_client import GeminiClient


def test_gemini_unconfigured_offline_fallback():
    client = GeminiClient(api_key="")
    assert client.is_configured is False

    res = client.review_code("print('hello')", "Python")
    assert res["status"] == "unconfigured"

    chat_reply = client.chat_with_repo("explain this", "context")
    assert "offline mode" in chat_reply.lower()


def test_gemini_quota_exhaustion_circuit_breaker(monkeypatch):
    client = GeminiClient(api_key="fake-test-key")

    mock_genai_client = MagicMock()
    # Simulate 429 quota exhausted error
    err = genai_errors.ClientError(429, {"error": {"message": "Resource exhausted: quota exceeded", "status": "RESOURCE_EXHAUSTED"}})
    mock_genai_client.models.generate_content.side_effect = err

    monkeypatch.setattr(client, "get_client", lambda: mock_genai_client)

    res1 = client.review_code("x = 1", "Python")
    assert res1["status"] == "failed"
    assert client.quota_exhausted is True

    # Next call should be immediately skipped by circuit breaker without hitting API
    res2 = client.review_code("x = 2", "Python")
    assert res2["status"] == "quota_exhausted"


def test_gemini_secrets_redacted_before_send(monkeypatch):
    client = GeminiClient(api_key="fake-test-key")

    captured_prompt = []
    mock_genai_client = MagicMock()
    def mock_gen(model, contents, config=None):
        captured_prompt.append(contents)
        mock_resp = MagicMock()
        mock_resp.text = '{"summary": "OK", "bugs": [], "improvements": [], "complexity_notes": "", "improved_code": "", "overall_score": 9}'
        return mock_resp

    mock_genai_client.models.generate_content.side_effect = mock_gen
    monkeypatch.setattr(client, "get_client", lambda: mock_genai_client)

    code_with_secret = 'API_KEY = "AKIA1234567890ABCDEF"\nprint(API_KEY)'
    res = client.review_code(code_with_secret, "Python")

    assert res["status"] == "ok"
    assert len(captured_prompt) == 1
    # Verify the secret plaintext was NOT transmitted to Gemini
    assert "AKIA1234567890ABCDEF" not in captured_prompt[0]
    assert "[REDACTED_AWS_KEY]" in captured_prompt[0]
