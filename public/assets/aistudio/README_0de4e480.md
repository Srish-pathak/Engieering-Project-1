# 🛰️ TecSpace Analyser

A code review dashboard for **Python, C++ and Java**. It combines a real syntax checker, rule-based static analysis,
measured complexity metrics and a Google **Gemini** review, then turns everything into one explainable quality score.

> Formerly "AI Code Reviewer". Same project, rebuilt and renamed.

## What it does

| Stage | What it does | Tool used |
|---|---|---|
| Syntax check | Finds code that cannot run, with line numbers | Python `compile()`, `g++ -fsyntax-only` (if installed) or tree-sitter, tree-sitter for Java |
| Static analysis | Finds likely mistakes without running the code | Python `ast`, tree-sitter |
| Complexity | Cyclomatic complexity per function, Maintainability Index (Python) | radon (Python), lizard (C++/Java) |
| AI review | Explains bugs, suggests improvements, writes improved code | Gemini API with a JSON schema |
| Score | Transparent score out of 10 | 60% rule-based + 40% AI |

Every complexity result is labelled **measured** (a real tool computed it) or **estimated** (keyword heuristic, used only
when no function can be detected).

### Static checks included

* **Python:** wrong function calls (missing/extra/unknown arguments, understands defaults, `*args`, `**kwargs`, keyword-only),
  undefined names, unused imports and variables, mutable default arguments, bare/swallowed `except`, `== None`, `is` with
  literals, division by zero, unreachable code, `while True` without exit, `eval`/`exec`, shadowed built-ins, redefined functions.
* **C++:** `strcpy`/`strcat`/`sprintf`/`scanf("%s")`/`gets`, assignment inside conditions, division by zero, empty `catch`,
  unreachable code, infinite loops, unused variables, possible memory leaks (`new` without `delete`).
* **Java:** string comparison with `==`, empty `catch`, division by zero, unreachable code, infinite loops, unused variables and imports.

Rules are deliberately conservative: it is better to miss a bug than to report one that is not there.

### Dashboard

Overview with score ring and metrics · filterable issue cards with the offending line · improvement suggestions ·
complexity breakdown · score explanation · original vs improved code with a diff · review history with score trend ·
downloadable reports (Markdown, HTML, JSON) · 12 ready-made test cases · file upload.

## Setup

```bash
git clone https://github.com/StudyTrigger/ai-code-reviewer.git tecspace-analyser   # or your renamed repo
cd tecspace-analyser
python -m venv .venv
.venv\Scripts\activate          # Windows      (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # Windows      (macOS/Linux: cp .env.example .env)
```

Open `.env` and set `GEMINI_API_KEY=your_key`. The `.env` file is git-ignored, so your key never reaches GitHub.
Without a key the app still works: syntax, static analysis and complexity run locally and AI review is disabled.

```bash
streamlit run app.py
```

## Run the tests

```bash
python -m pytest -q
```

The suite (92 tests) covers the analyzers, the scoring, the Gemini pipeline using a fake client (retries, quota errors,
invalid JSON, invalid improved code) and the dashboard itself using Streamlit's headless test runner. It does **not** call
the real Gemini API.

## Project structure

```text
app.py              Streamlit dashboard
reviewer.py         Review pipeline + Gemini call, retries, validation
syntax_checker.py   Syntax validation (Python / C++ / Java)
static_analysis.py  Rule-based bug finding
complexity.py       Cyclomatic complexity + Maintainability Index
utils.py            Scoring, JSON parsing, bug merging, history
report.py           Markdown / HTML / JSON reports
samples.py          Ready-made test cases
test.py             Lists the Gemini models your key can use
test_*.py           Automated tests
```

## Security

* The API key is read only from the `GEMINI_API_KEY` environment variable / `.env`; it is never printed or stored.
* AI output is HTML-escaped before display. Submitted code is treated as data in the prompt, not as instructions.
* For C++, the syntax check runs `g++ -fsyntax-only` on a temporary file (it compiles but never executes your code).
  Do not expose this app publicly with untrusted users without sandboxing.
* Review history is saved to `review_history.json` (git-ignored). Set `TECSPACE_SAVE_HISTORY=0` on shared deployments.

## Known limitations

* Syntax checking for C++ is exact only when `g++` is installed; otherwise tree-sitter checks grammar but not types or declarations.
  Java is grammar-checked (no `javac` type checking).
* Function-call checking is Python-only (C++/Java have overloading, so it is left to the compiler/AI).
* The Maintainability Index is Python-only.
* AI review quality depends on the model; the score blends it at only 40% so rule-based findings dominate.
* The default model name is `gemini-3.5-flash`. If Google retires it, set `GEMINI_MODEL` in `.env`.

## Author

Mahesh Verma (Study Trigger) · [LinkedIn](https://www.linkedin.com/in/studytrigger/) · MIT License.
