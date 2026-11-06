import unittest

from local_checks import run_local_checks


class LocalCheckTests(unittest.TestCase):
    def text(self, code, language="Python"):
        return " ".join(f["description"] for f in run_local_checks(code, language))

    def test_clean_python(self):
        self.assertEqual(run_local_checks("def add(a, b):\n    return a + b\n", "Python"), [])

    def test_risky_python(self):
        text = self.text("import os\ndef f(x, y=[]):\n    try:\n        eval(x)\n    except:\n        pass\n")
        for part in ("never used", "mutable default", "eval", "Bare"):
            self.assertIn(part, text)

    def test_secret_in_any_language(self):
        findings = run_local_checks('const apiKey = "abcd1234efgh5678";', "JavaScript")
        self.assertTrue(any(f["severity"] == "critical" for f in findings))

    def test_javascript(self):
        text = self.text("var a = 1;\nif (a == 2) console.log(a);\n", "JavaScript")
        for part in ("let", "===", "console.log"):
            self.assertIn(part, text)

    def test_syntax_error_does_not_crash(self):
        self.assertIsInstance(run_local_checks("def broken(:\n", "Python"), list)


if __name__ == "__main__":
    unittest.main()
