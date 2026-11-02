"""Headless UI tests: drives the real Streamlit script with streamlit.testing (no browser needed).
The code editor component is switched off so the plain text-area fallback is used."""
import json
import sys

import pytest
from google.genai import errors as genai_errors
from streamlit.testing.v1 import AppTest

import reviewer
import utils
from samples import SAMPLES

from test_reviewer import FakeClient, ai_json


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "streamlit_ace", None)            # use the text_area fallback
    monkeypatch.setattr(utils, "HISTORY_FILE", tmp_path / "history.json")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(reviewer, "RETRY_DELAY_SECONDS", 0)


def new_app():
    at = AppTest.from_file("app.py", default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def click(at, label):
    next(b for b in at.button if b.label == label).click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def page_text(at):
    parts = [m.value for m in at.markdown] + [i.value for i in at.info] + [w.value for w in at.warning]
    parts += [s.value for s in at.success] + [e.value for e in at.error]
    return "\n".join(parts)


def test_app_loads_with_default_sample_and_title():
    at = new_app()
    assert "TecSpace Analyser" in page_text(at)
    assert "calculate_total" in at.text_area[0].value
    assert any("GEMINI_API_KEY" in w.value for w in at.sidebar.warning)   # no key -> clear message


def test_local_analysis_works_without_api_key():
    at = new_app()
    click(at, "Analyze code")
    text = page_text(at)
    assert "missing required argument" in text and "is not defined" in text
    assert 'class="ts-ring"' in text and len(at.tabs) >= 7


@pytest.mark.parametrize("language", list(SAMPLES))
def test_every_sample_runs_without_crashing(language):
    at = new_app()
    at.sidebar.selectbox(key="language").select(language).run()
    for name in SAMPLES[language]:
        at.sidebar.selectbox(key=f"sample_{language}").select(name).run()
        assert at.text_area[0].value == SAMPLES[language][name]
        click(at, "Analyze code")
        assert 'class="ts-ring"' in page_text(at), (language, name)


def test_syntax_error_sample_shows_critical_issue():
    at = new_app()
    at.sidebar.selectbox(key="sample_Python").select("Syntax error").run()
    click(at, "Analyze code")
    assert "Syntax error detected" in page_text(at) and "SyntaxError" in page_text(at)


def test_empty_editor_warns():
    at = new_app()
    at.text_area[0].set_value("   ").run()
    click(at, "Analyze code")
    assert any("empty" in w.value.lower() for w in at.warning)


def test_ai_review_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    monkeypatch.setattr(reviewer, "get_client", lambda: FakeClient([ai_json(bugs=[], summary="Fake AI summary.")]))
    at = new_app()
    assert at.sidebar.toggle[0].value is True
    click(at, "Analyze code")
    assert "Fake AI summary." in page_text(at) and "Add type hints" in page_text(at)
    assert "passed the syntax" in page_text(at)


def test_ai_failure_still_shows_local_results(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    err = genai_errors.ClientError(429, {"error": {"message": "quota", "status": "RESOURCE_EXHAUSTED"}})
    monkeypatch.setattr(reviewer, "get_client", lambda: FakeClient([err, err, err]))
    at = new_app()
    click(at, "Analyze code")
    text = page_text(at)
    assert "AI review unavailable" in text and "quota" in text.lower()
    assert "missing required argument" in text          # local findings still present


def test_ai_text_is_html_escaped(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")
    evil = ai_json(bugs=[{"line": "1", "severity": "info", "description": "<script>alert(1)</script>", "fix": ""}])
    monkeypatch.setattr(reviewer, "get_client", lambda: FakeClient([evil]))
    at = new_app()
    click(at, "Analyze code")
    assert "<script>alert(1)</script>" not in page_text(at)
    assert "&lt;script&gt;" in page_text(at)


def test_history_is_saved_and_can_be_reopened(tmp_path):
    at = new_app()
    click(at, "Analyze code")
    saved = json.loads((tmp_path / "history.json").read_text(encoding="utf-8"))
    assert len(saved) == 1 and saved[0]["language"] == "Python"
    at.sidebar.selectbox(key="sample_Python").select("Clean code").run()   # clears current results
    assert 'class="ts-ring"' not in page_text(at)
    # a fresh session reloads history from disk and can reopen the review
    at2 = new_app()
    next(b for b in at2.button if b.label == "Open review").click()
    at2.run()
    assert not at2.exception and 'class="ts-ring"' in page_text(at2)
    assert "calculate_total" in at2.text_area[0].value


def test_clear_results_button():
    at = new_app()
    click(at, "Analyze code")
    click(at, "Clear results")
    assert 'class="ts-ring"' not in page_text(at)
