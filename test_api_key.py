import pytest

from reviewer import get_client


def test_get_client_raises_when_key_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(EnvironmentError):
        get_client()


def test_get_client_rejects_placeholder_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "YOUR_API_KEY")
    with pytest.raises(EnvironmentError):
        get_client()


def test_get_client_builds_client_when_key_present(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-test")
    assert get_client() is not None  # builds the object only; no network call is made
