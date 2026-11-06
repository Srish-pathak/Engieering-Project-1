# 🔍 AI Code Reviewer (with GitHub repo analysis)

Streamlit app that reviews code with offline static analysis plus **Google Gemini** (free tier works).
Paste code, or paste a **public GitHub repository URL** and get a per-file and repo-wide report.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Get a free key at https://aistudio.google.com/apikey and either paste it in the sidebar, or copy
`.env.example` to `.env` and set `GEMINI_API_KEY`. With no key, the offline checks still work.

## Features

| Area | What it does |
| --- | --- |
| Check my code | Syntax check, call-signature analysis, security/quality patterns, Radon complexity, Gemini review, score, before/after, .md/.json export |
| Analyse a GitHub repo | Fetches up to 30 supported files (Python first), reviews each one, shows an overview table, per-file details and a downloadable report |
| Languages | Python, C++, Java, JavaScript, JSX, TypeScript, TSX, HTML, CSS, SCSS |

## GitHub analysis notes

- Public repos only; no GitHub token needed. GitHub allows 60 unauthenticated requests/hour and each file costs one.
- Skips `node_modules`, `venv`, `dist`, `build`, hidden folders, binaries and files over 200 KB.
- Each file is isolated: one failure never stops the rest.
- Free Gemini keys have low per-minute/day limits. Start with 5-10 files. If the quota is hit, the app stops calling
  Gemini and finishes the remaining files with offline checks. Untick **Use Gemini AI** for a quota-free run.

## Configuration

| Setting | Purpose |
| --- | --- |
| Sidebar key | Session-only key, highest priority |
| `GEMINI_API_KEY` | Environment variable, `.env`, or Streamlit secret |
| `GEMINI_MODEL` or sidebar Model box | Default `gemini-2.5-flash`. If you get "model not available", list your models in AI Studio and change it |

## Structure

```text
app.py              Streamlit UI (code tab + GitHub tab)
reviewer.py         Gemini calls, error handling, per-file and repo orchestration
github_fetcher.py   Public repository fetching
local_checks.py     Offline security / quality heuristics
static_analysis.py  AST call-argument checks
syntax_checker.py   Python syntax validation
complexity.py       Radon (Python) / heuristic (others)
report.py           Markdown / JSON reports
utils.py            JSON parsing and display helpers
test_*.py           Tests (no network, no API credit)
```

## Tests

```bash
pytest -q
```

## Privacy

When AI review is on, source code is sent to Google Gemini. Free-tier prompts may be used by Google to improve its products. Do not submit code you cannot share.
