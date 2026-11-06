import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import reviewer
from complexity import analyze_complexity
from reviewer import classify_error, review_code, review_repo_files
from static_analysis import analyze_static
from syntax_checker import check_syntax
from utils import safe_json_parse

GOOD_JSON = (
    '{"summary":"Looks fine","bugs":[{"line":1,"severity":"warning","description":"Check this"}],'
    '"improvements":[{"title":"Rename","detail":"Clearer name"}],"complexity_notes":"Low",'
    '"overall_score":7,"improved_code":"print(2)"}'
)


def client_returning(text):
    def generate_content(**kwargs):
        return SimpleNamespace(text=text)
    return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))


def client_failing(exc):
    def generate_content(**kwargs):
        raise exc
    return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))


class ReviewCodeTests(unittest.TestCase):
    def test_successful_ai_review_is_merged_with_offline_findings(self):
        with patch("reviewer.get_client", return_value=client_returning(GOOD_JSON)):
            result = review_code("import os\nprint(1)\n", "Python")
        self.assertEqual(result["analysis_status"]["ai"], "completed")
        self.assertEqual(result["overall_score"], 7)
        descriptions = " ".join(b["description"] for b in result["bugs"])
        self.assertIn("never used", descriptions)  # offline finding
        self.assertIn("Check this", descriptions)  # AI finding
        self.assertEqual(result["bugs"][-1]["severity"], "Medium")  # 'warning' normalised

    def test_syntax_error_skips_ai(self):
        with patch("reviewer.get_client") as client:
            result = review_code("def broken(:\n", "Python")
        client.assert_not_called()
        self.assertEqual(result["analysis_status"]["ai"], "not_run")
        self.assertEqual(result["bugs"][0]["severity"], "critical")

    def test_empty_code(self):
        self.assertTrue(review_code("  \n", "Python")["error"])

    def test_offline_mode_never_calls_ai(self):
        with patch("reviewer.get_client") as client:
            result = review_code("def f(x):\n    eval(x)\n", "Python", use_ai=False)
        client.assert_not_called()
        self.assertEqual(result["analysis_status"]["ai"], "skipped")
        self.assertTrue(any("eval" in b["description"] for b in result["bugs"]))

    def test_missing_key_keeps_offline_findings(self):
        with patch.dict(os.environ, {}, clear=True), patch("reviewer._secret", return_value=None):
            result = review_code("def f(x):\n    eval(x)\n", "Python")
        self.assertEqual(result["analysis_status"]["ai"], "missing_key")
        self.assertTrue(any("eval" in b["description"] for b in result["bugs"]))

    def test_malformed_json_is_reported(self):
        with patch("reviewer.get_client", return_value=client_returning("not json")):
            result = review_code("print(1)\n", "Python")
        self.assertEqual(result["analysis_status"]["ai"], "invalid_response")

    def test_request_uses_selected_model_and_json_mode(self):
        seen = {}

        def generate_content(**kwargs):
            seen.update(kwargs)
            return SimpleNamespace(text=GOOD_JSON)

        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with patch("reviewer.get_client", return_value=client):
            review_code("print(1)\n", "Python", model="my-model")
        self.assertEqual(seen["model"], "my-model")
        self.assertEqual(seen["config"]["response_mime_type"], "application/json")


class ErrorClassificationTests(unittest.TestCase):
    def test_statuses(self):
        cases = {
            "400 API key not valid. Please pass a valid API key.": "invalid_api_key",
            "429 RESOURCE_EXHAUSTED quota exceeded": "rate_limited",
            "403 PERMISSION_DENIED": "permission_denied",
            "404 models/foo is not found": "model_unavailable",
            "Request timed out": "timeout",
        }
        for text, expected in cases.items():
            self.assertEqual(classify_error(RuntimeError(text))[0], expected, text)

    def test_missing_key_error(self):
        self.assertEqual(classify_error(reviewer.MissingKeyError("x"))[0], "missing_key")

    def test_rate_limit_retries_once_then_succeeds(self):
        calls = {"n": 0}

        def generate_content(**kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("429 RESOURCE_EXHAUSTED retry in 2s")
            return SimpleNamespace(text=GOOD_JSON)

        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        with patch("reviewer.get_client", return_value=client), patch("reviewer.time.sleep") as sleep:
            result = review_code("print(1)\n", "Python")
        self.assertEqual(calls["n"], 2)
        sleep.assert_called_once()
        self.assertEqual(result["analysis_status"]["ai"], "completed")


class KeyHandlingTests(unittest.TestCase):
    def test_clean_key(self):
        self.assertEqual(reviewer.clean_key('  "Bearer AIzaABC" '), "AIzaABC")

    def test_sidebar_key_beats_environment(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "from-env"}):
            self.assertEqual(reviewer.resolve_key("pasted"), "pasted")
            self.assertEqual(reviewer.resolve_key(None), "from-env")


class RepoReviewTests(unittest.TestCase):
    FILES = [{"path": "a.py", "language": "Python", "content": "print(1)\n"},
             {"path": "b.py", "language": "Python", "content": "print(2)\n"},
             {"path": "c.py", "language": "Python", "content": "print(3)\n"}]

    def test_aggregates_scores(self):
        with patch("reviewer.get_client", return_value=client_returning(GOOD_JSON)):
            summary = review_repo_files(self.FILES, delay_seconds=0)
        self.assertEqual(summary["files_reviewed"], 3)
        self.assertEqual(summary["ai_reviewed_files"], 3)
        self.assertEqual(summary["overall_score"], 7.0)
        self.assertEqual(summary["severity_counts"]["medium"], 3)

    def test_ai_stops_after_quota_but_offline_continues(self):
        client = client_failing(RuntimeError("429 RESOURCE_EXHAUSTED"))
        with patch("reviewer.get_client", return_value=client):
            summary = review_repo_files(self.FILES, delay_seconds=0)
        self.assertEqual(summary["files_reviewed"], 3)
        self.assertEqual(summary["ai_failed_files"], 1)  # later files skip AI instead of failing again
        self.assertIsNotNone(summary["ai_stopped_reason"])
        self.assertIsNone(summary["overall_score"])

    def test_one_crashing_file_does_not_stop_the_rest(self):
        real = reviewer.review_code

        def flaky(code, language, path, *args, **kwargs):
            if path == "b.py":
                raise RuntimeError("boom")
            return real(code, language, path, *args, **kwargs)

        with patch("reviewer.review_code", side_effect=flaky):
            summary = review_repo_files(self.FILES, use_ai=False)
        self.assertEqual(summary["files_reviewed"], 3)
        self.assertTrue(summary["file_results"][1]["review"]["error"])

    def test_progress_callback(self):
        seen = []
        review_repo_files(self.FILES, lambda d, t, p: seen.append((d, t, p)), use_ai=False)
        self.assertEqual(seen[-1], (3, 3, "c.py"))


class AnalysisHelperTests(unittest.TestCase):
    def test_static_accepts_defaults_and_keywords(self):
        code = 'def greet(name, p="!"):\n    return name + p\n\ngreet("A")\ngreet(name="A", p="?")\n'
        self.assertEqual(analyze_static(code, "Python"), [])

    def test_static_flags_bad_calls(self):
        code = "def add(a, b):\n    return a + b\n\nadd(1)\nadd(1, 2, 3)\n"
        self.assertEqual(len(analyze_static(code, "Python")), 2)

    def test_syntax_bugs_are_a_list(self):
        self.assertIsInstance(check_syntax("def x(:\n", "Python")["bugs"], list)

    def test_complexity(self):
        code = "def f(v):\n    if v > 0:\n        if v > 10:\n            return 3\n        return 2\n    return 1\n"
        result = analyze_complexity(code, "Python")
        self.assertIn(result["method"], {"radon", "heuristic"})
        self.assertGreater(result["average_complexity"], 1)

    def test_json_from_fenced_response(self):
        self.assertEqual(safe_json_parse('x\n```json\n{"summary":"ok"}\n```')["summary"], "ok")


if __name__ == "__main__":
    unittest.main()
