import os
import sys

from reviewer import get_client


def test_get_client_uses_default_key_when_env_missing(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = get_client()
    assert client is not None
