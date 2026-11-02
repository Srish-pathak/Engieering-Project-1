# TechSpecAnalyser — A Static-Analysis-Grounded Multi-Agent System for Automated Code Review and Documentation Generation

**Submitted by:** Srishti Pathak  
**Programme:** Integrated M.Tech in Computer Science & Engineering  
**Department:** Department of Computer Science and Engineering, Central University of Jharkhand (2026)

---

## 1. Project Overview

**TechSpecAnalyser** (evolved from *TecSpace Analyser*) is a full-stack intelligent software-engineering platform that combines deterministic program analysis (`ast`, `tokenize`, `compile()`, `radon`/`lizard` cyclomatic complexity, and static security/bug rules) with six specialized **Google Gemini** AI review agents coordinated by a central **Review Orchestrator** and **Review Synthesizer**.

### Core Engineering Principle
> **Never send raw code to a single AI model and rely blindly on its opinion.**  
> TechSpecAnalyser first extracts deterministic, measurable program facts via AST parsing, static rules, and software metrics. Those facts ground six specialized AI review agents, whose observations are deduplicated and separated from confirmed static findings.

---

## 2. System Architecture

```text
User / Developer
      │
      ├───────────────────────────┬───────────────────────────┐
      ▼                           ▼                           ▼
 Paste Code              Single File Upload          Project ZIP Upload
 (.py / .cpp / .java)    (.py / .cpp / .java)        (Path-Traversal Guard)
      │                           │                           │
      └───────────────────────────┼───────────────────────────┘
                                  ▼
                 Source Input Manager & AST Parser
                                  │
            ┌─────────────────────┼─────────────────────┐
            ▼                     ▼                     ▼
     AST Structural      Deterministic Static     Software Metrics
     Fact Extractor         Analysis Rules        (McCabe CC & MI)
            │                     │                     │
            └─────────────────────┼─────────────────────┘
                                  ▼
                     Review Orchestrator (/api/analyze)
                                  │
   ┌──────────────┬───────────────┼───────────────┬──────────────┬──────────────┐
   ▼              ▼               ▼               ▼              ▼              ▼
Quality     Simplification    Security       Complexity     Type / API    Documentation
 Agent          Agent          Agent           Agent          Agent          Agent
   │              │               │               │              │              │
   └──────────────┴───────────────┼───────────────┴──────────────┴──────────────┘
                                  ▼
                  Review Synthesizer & Diff Validator
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
     Consolidated Review Report       Automated Documentation & README
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
             React + TypeScript + Tailwind Web Workbench
             & SQLite Persistence (backend/codelens.db)
```

---

## 3. Project Folder Structure

```text
/
├── backend/
│   ├── codelens_engine.py       # Python AST extractor, 14 static rules, McCabe CC & Halstead MI,
│   │                            # Documentation generator, ZIP validator, SQLite DB & Benchmark engine
│   ├── fastapi_app.py           # Standalone FastAPI REST server (optional direct Python server)
│   └── tests/
│       └── test_codelens.py     # 16-scenario automated unit & integration test suite
├── src/
│   ├── App.tsx                  # Full 7-page TechSpecAnalyser React workbench (Dark/Light mode)
│   ├── main.tsx                 # React entry point
│   ├── index.css                # Tailwind v4 + IBM Plex Sans & JetBrains Mono configuration
│   ├── data/
│   │   └── codelensSamples.ts   # 13 ready-made test cases, ZIP generators, Viva demo script & Matrix
│   └── utils/
│       └── reportExporter.ts    # Markdown (.md), Standalone HTML (.html), and JSON (.json) exporters
├── server.ts                    # Full-stack Express + Vite server bridging Python AST engine & @google/genai
├── requirements.txt             # Python dependencies
├── package.json                 # Node/React/TypeScript dependencies & scripts
├── .env.example                 # Environment variable template (never commit secrets)
└── README.md                    # Complete setup, API, architecture, and viva demonstration guide
```

---

## 4. API Endpoint Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Returns server health, active Gemini model name, and whether `GEMINI_API_KEY` is configured. |
| `POST` | `/api/analyze` | Runs the 5-stage pipeline (Syntax Gate → AST & Static Analysis → McCabe CC & MI → 6-Agent Orchestrator → Synthesizer & SQLite save). |
| `POST` | `/api/upload-zip` | Validates a base64 `.zip` archive against path traversal (`..`), filters `.venv`/`node_modules`/`__pycache__`, and analyzes all source files. |
| `POST` | `/api/import-github` | Connects directly to any public GitHub repository (`owner/repo` or URL), downloads its tree via GitHub REST API, and runs the full multi-agent pipeline. |
| `GET` | `/api/history` | Loads the 25 most recent review runs from the SQLite database (`backend/codelens.db`). |
| `DELETE` | `/api/history` | Clears stored review runs from SQLite. |
| `GET` | `/api/evaluate` | Runs the reproducible Experimental Evaluation comparing Approach A, Approach B, and Approach C on ground-truth annotated datasets. |

---

## 5. Live Deployment & Dual-Runtime Execution Guide

### Live Streamlit Community Cloud Deployment
- **Live URL:** [https://code-visualiser-python-n4usxyvc8j48unplx6kh3m.streamlit.app/](https://code-visualiser-python-n4usxyvc8j48unplx6kh3m.streamlit.app/)
- Root-level Streamlit files (`app.py`, `reviewer.py`, `static_analysis.py`, `syntax_checker.py`, `complexity.py`, `utils.py`, `report.py`, `samples.py`, `requirements.txt`) are maintained in sync with `backend/codelens_engine.py` so pushing this GitHub repository updates your Streamlit Community Cloud deployment automatically.

### Prerequisites
- **Node.js** `>= 18`
- **Python** `>= 3.10`

### Step 1: Install Dependencies
```bash
npm install
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` and add your Gemini API key:
```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY="your_key_here"
```
*(Note: Without an API key, TechSpecAnalyser automatically runs in deterministic offline mode—syntax checking, AST static rules, McCabe complexity, Maintainability Index, documentation generation, and experimental evaluation all work without an API key.)*

### Step 3: Run the Automated Test Suite
```bash
python3 -m unittest discover -s backend/tests -v
pytest -q
```

### Step 4: Start Either Runtime
- **Full-Stack React + Express + Python Workbench (Port 3000):**
  ```bash
  npm run dev
  ```
- **Streamlit Dashboard (`app.py`):**
  ```bash
  streamlit run app.py
  ```

