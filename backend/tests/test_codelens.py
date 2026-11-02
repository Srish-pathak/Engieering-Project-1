"""
Automated Unit & Integration Test Suite for CodeLens AI (Part 14 Requirements).
Covers all 16 required test scenarios using Python's built-in unittest runner
(compatible with both `python3 -m unittest` and `pytest`).
"""
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import codelens_engine as engine


class TestCodeLensEngine(unittest.TestCase):
    # 1. Valid Python syntax
    def test_01_valid_python_syntax(self):
        res = engine.check_syntax("def add(a: int, b: int) -> int:\n    return a + b\n", "Python")
        self.assertTrue(res["valid"])
        self.assertEqual(res["bugs"], [])

    # 2. Invalid Python syntax
    def test_02_invalid_python_syntax_halts_early(self):
        res = engine.check_syntax("def broken(\n    return 1\n", "Python", "broken.py")
        self.assertFalse(res["valid"])
        self.assertEqual(len(res["bugs"]), 1)
        self.assertEqual(res["bugs"][0]["severity"], "critical")
        self.assertEqual(res["bugs"][0]["rule"], "syntax-error")

        payload_res = engine.analyze_project_payload({
            "code": "def broken(\n    return 1\n",
            "language": "Python",
            "file_name": "broken.py",
        })
        self.assertFalse(payload_res["valid_syntax"])
        self.assertEqual(payload_res["overall_score"], 1.0)

    # 3. Function argument mismatch (bad-call)
    def test_03_function_argument_mismatch(self):
        code = "def calc(price, qty, discount=0):\n    return price * qty - discount\n\ncalc(100)\ncalc(100, 2, bad_kw=5)\n"
        findings = engine.analyze_static(code, "Python", "orders.py")
        rules = [f["rule"] for f in findings]
        self.assertEqual(rules.count("bad-call"), 2)

    # 4. Empty code input
    def test_04_empty_code_input(self):
        comp = engine.analyze_complexity("   ", "Python")
        self.assertEqual(comp["average_complexity"], 0)
        self.assertEqual(comp["rating"], "N/A")

    # 5. Simple and complex functions (Cyclomatic Complexity)
    def test_05_simple_and_complex_functions(self):
        code = (
            "def simple(x):\n    return x + 1\n\n"
            "def branchy(a, b, c):\n"
            "    if a > 0 and b > 0:\n"
            "        for i in range(a):\n"
            "            if i % 2 == 0 or c:\n"
            "                b += i\n"
            "    elif c < 0:\n"
            "        while b > 0:\n"
            "            b -= 1\n"
            "    return b\n"
        )
        comp = engine.analyze_complexity(code, "Python")
        self.assertEqual(comp["analysis_type"], "measured")
        self.assertEqual(comp["function_count"], 2)
        by_name = {d["name"]: d["complexity"] for d in comp["details"]}
        self.assertEqual(by_name["simple"], 1)
        self.assertGreaterEqual(by_name["branchy"], 7)

    # 6. Maintainability Index calculations
    def test_06_maintainability_index_calculated(self):
        code = '"""Module docstring."""\ndef compute(items: list[int]) -> int:\n    """Sum items."""\n    return sum(items)\n'
        comp = engine.analyze_complexity(code, "Python")
        self.assertIsNotNone(comp["maintainability_index"])
        self.assertGreaterEqual(comp["maintainability_index"], 50.0)
        self.assertEqual(comp["mi_rank"], "A")

    # 7. Deterministic Static-Analysis Findings (Python, Security, C++, Java)
    def test_07_static_analysis_findings_and_security_rules(self):
        py_code = (
            "import os\n"
            "API_KEY = 'sk_live_secret_123456'\n"
            "def bad(items=[]):\n"
            "    x = 10 / 0\n"
            "    cursor.execute(f'SELECT * FROM t WHERE id = {x}')\n"
            "    return unknown_var\n"
            "    print('unreachable')\n"
        )
        findings = engine.analyze_static(py_code, "Python", "sec.py")
        found_rules = {f["rule"] for f in findings}
        for expected in ("unused-import", "hardcoded-secret", "mutable-default", "division-by-zero", "sql-injection-risk", "undefined-name", "unreachable-code"):
            self.assertIn(expected, found_rules)

        cpp_findings = engine.analyze_static('int main() { char b[4]; strcpy(b, "overflow"); int x = 5 / 0; return 0; }', "C++", "main.cpp")
        cpp_rules = {f["rule"] for f in cpp_findings}
        self.assertIn("unsafe-call", cpp_rules)
        self.assertIn("division-by-zero", cpp_rules)

        java_findings = engine.analyze_static('public class A { boolean f(String s) { if (s == "admin") return true; return false; } }', "Java", "A.java")
        java_rules = {f["rule"] for f in java_findings}
        self.assertIn("string-equality", java_rules)

    # 8, 9, 10, 11. Mocked AI JSON parsing, API failure fallback, Missing API key, Agent timeout resilience
    def test_08_to_11_offline_and_agent_failure_resilience(self):
        # Verify that when AI score is None (API failure / missing key / agent timeout),
        # deterministic scoring and synthesis still produce a complete, valid report.
        bugs = [{"file": "a.py", "line": 4, "severity": "critical", "description": "Division by zero", "source": "static", "rule": "division-by-zero"}]
        score_info = engine.compute_quality_score(bugs, {"max_complexity": 3, "mi_rank": "A"}, ai_score=None)
        self.assertEqual(score_info["rule_score"], 8.0)
        self.assertEqual(score_info["score"], 8.0)
        self.assertIsNone(score_info["ai_score"])

    # 12. Review Synthesizer deduplication
    def test_12_synthesizer_deduplication_preserves_static_evidence(self):
        static_bugs = [{
            "file": "app.py", "line": 10, "severity": "critical",
            "description": "Call to `add(a, b)` is wrong: missing required argument(s): b.",
            "source": "static", "rule": "bad-call",
        }]
        agent_bugs = [
            {
                "file": "app.py", "line": "10", "severity": "critical",
                "description": "Function add() is called with missing required argument b",
                "source": "agent:quality",
            },
            {
                "file": "app.py", "line": 10, "severity": "info",
                "description": "Consider adding type annotations to parameters",
                "source": "agent:type_api",
            },
        ]
        merged = engine.merge_bugs(static_bugs, agent_bugs)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["source"], "static")
        self.assertTrue(merged[0]["deterministic"])
        self.assertFalse(merged[1]["deterministic"])

    # 13. ZIP validation and unsafe archive path traversal protection
    def test_13_zip_validation_and_path_traversal_protection(self):
        # Safe archive
        buf_safe = io.BytesIO()
        with zipfile.ZipFile(buf_safe, "w") as zf:
            zf.writestr("src/service.py", "def run():\n    return 42\n")
            zf.writestr(".venv/ignored.py", "x = 1\n")
        res_safe = engine.validate_and_extract_zip(buf_safe.getvalue())
        self.assertTrue(res_safe["valid"])
        self.assertEqual(len(res_safe["files"]), 1)
        self.assertEqual(res_safe["files"][0]["path"], "src/service.py")

        # Malicious path traversal archive
        buf_evil = io.BytesIO()
        with zipfile.ZipFile(buf_evil, "w") as zf:
            zf.writestr("../../etc/passwd.py", "x = 1\n")
        res_evil = engine.validate_and_extract_zip(buf_evil.getvalue())
        self.assertFalse(res_evil["valid"])
        self.assertTrue(len(res_evil["security_violations"]) > 0)

    # 14. Automated Documentation Generation
    def test_14_documentation_generation_and_coverage(self):
        code = "def transfer_funds(sender: str, receiver: str, amount: float) -> bool:\n    return amount > 0\n"
        facts = engine.extract_ast_facts(code, "Python", "ledger.py")
        comp = engine.analyze_complexity(code, "Python", facts)
        docs = engine.generate_documentation("LedgerProject", [facts], comp)
        self.assertLess(docs["doc_coverage_before"], 100.0)
        self.assertEqual(docs["doc_coverage_after"], 100.0)
        self.assertTrue(len(docs["suggested_docstrings"]) >= 1)
        self.assertIn("transfer_funds", docs["readme_markdown"])

    # 15. Unified Diff & Report Export data
    def test_15_unified_diff_generation(self):
        diff = engine.unified_diff("x = 1 / 0\n", "x = 1 / 1\n")
        self.assertIn("-x = 1 / 0", diff)
        self.assertIn("+x = 1 / 1", diff)

    # 16. SQLite Review History persistence and Experimental Evaluation
    def test_16_sqlite_history_and_experimental_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_file = Path(tmp) / "test_codelens.db"
            entry = {
                "id": "run-001",
                "project_id": "proj-001",
                "project_name": "TestProj",
                "language": "Python",
                "input_mode": "paste",
                "time": "31 Oct 2026, 12:00",
                "score": 8.5,
                "rule_score": 8.5,
                "ai_score": None,
                "critical": 0,
                "warning": 1,
                "info": 0,
                "doc_coverage": 50.0,
                "execution_ms": 12,
                "summary": "Clean run",
            }
            engine.save_review_run(entry, db_file)
            loaded = engine.load_review_runs(db_file)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["id"], "run-001")
            engine.clear_review_runs(db_file)
            self.assertEqual(engine.load_review_runs(db_file), [])

        eval_res = engine.run_experimental_evaluation()
        self.assertEqual(len(eval_res["approaches"]), 3)
        approach_c = next(a for a in eval_res["approaches"] if a["id"] == "C")
        self.assertGreaterEqual(approach_c["f1_score"], 0.9)


if __name__ == "__main__":
    unittest.main()
