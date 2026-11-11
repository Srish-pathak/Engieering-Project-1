# TechSpecAnalyser — Advanced AI-Powered Code Intelligence & Security Platform

> **Tagline:** *Your Intelligent AI-Powered Code Review, Security & Repository Intelligence Platform.*

TechSpecAnalyser is a software engineering intelligence platform combining deterministic program analysis (Python AST, Tree-Sitter CST, Radon cyclomatic complexity, Halstead maintainability, and multi-language static security rules) with Google Gemini AI reasoning.

It provides repository-level code understanding, CWE vulnerability audits, secret redactions, optimization diffs, automated GitHub push webhook monitoring, and interactive codebase chat with persistent SQLite tracking.

---

## 1. System Architecture

```text
                                User / Developer
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
     Streamlit Workbench                           FastAPI Webhook Service
      (streamlit run app.py)                     (uvicorn api:app --port 8000)
               │                                             │
               ├──────────────────────┬──────────────────────┤
               ▼                      ▼                      ▼
         Paste / File          GitHub REST API        GitHub Push Webhook
         Source Code           Tree & Commits         (HMAC Verification)
               │                      │                      │
               └──────────────────────┼──────────────────────┘
                                      ▼
                      Multi-Language Analysis Dispatcher
      ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼              ▼              ▼              ▼
    Python         C / C++         Java      JS / JSX / TS       Web          Security
   (AST/Radon)  (g++/TreeSitter) (TreeSitter)   (Lizard/AST)  (HTML/CSS)     (CWE Engine)
      │              │              │              │              │              │
      └──────────────┴──────────────┼──────────────┴──────────────┴──────────────┘
                                    ▼
                      Secret Redaction Sanitizer
                     (Purges AWS/GH/Keys/Passwords)
                                    ▼
                      Google Gemini AI Reasoning
                (gemini-2.5-flash / Configurable Model)
                                    ▼
                     4-Pillar Transparent Scoring
              (30% Security + 30% Bugs + 20% MI + 20% CC)
                                    ▼
                      SQLite Persistence & Reports
             (techspec.db, Plotly Trends, Markdown/JSON/CSV)
```

---

## 2. Core Capabilities & Workflows

### Workflow A: Individual Code Review (Pasted & File Uploads)
- **Multi-Language Support:** Python (`.py`), C (`.c`, `.h`), C++ (`.cpp`, `.cc`, `.cxx`, `.hpp`), Java (`.java`), JavaScript (`.js`, `.mjs`, `.cjs`), JSX (`.jsx`), TypeScript (`.ts`), TSX (`.tsx`), HTML (`.html`), CSS (`.css`), and SCSS (`.scss`).
- **Early Syntax Gate:** Halts invalid syntax before AI invocations with exact compiler or grammar line numbers.
- **Deterministic Findings:** Flags arity mismatches, undefined variables, division by zero, empty catches, loose equality, and unclosed resources without hallucination.
- **AI-Powered Fixes:** Syntax-validated improved code with side-by-side and unified diff viewers.

### Workflow B: Real GitHub Repository Intelligence
- Connect any public or private GitHub repository via URL or slug (`owner/repo`).
- Inspect default branch, branch list, commit history, and directory tree.
- Built-in safeguards: 30 files analyzed by default, 200 KB per-file limit, exclusions for `node_modules`, `.venv`, `dist`, `build`, and binary files.
- Fault-isolated per-file processing: one corrupted or oversized file never halts the review.
- Generates comprehensive grounded technical architecture reports and `PROJECT_DOCUMENTATION.md`.

### Workflow C: Dedicated Security Audit & Secret Redaction
- Scans for common vulnerability patterns mapped to CWE IDs:
  - **CWE-798:** Hardcoded Credentials & API Keys
  - **CWE-89:** SQL Injection via String Concatenation & Interpolation
  - **CWE-78:** OS Command Injection (`os.system`, `subprocess`, `shell=True`)
  - **CWE-502:** Unsafe Deserialization (`pickle.loads`, `yaml.load`)
  - **CWE-79:** Cross-Site Scripting (`dangerouslySetInnerHTML`, `innerHTML`)
  - **CWE-22:** Path Traversal Risks
  - **CWE-327:** Broken Cryptographic Algorithms (MD5, SHA-1)
  - **CWE-295:** Disabled SSL Certificate Validation (`verify=False`)
  - **CWE-942:** Overly Permissive CORS (`allow_origins=["*"]`)
  - **CWE-120:** Unbounded Buffer Overflows (`gets`, `strcpy`)
- Automatic secret redaction: masks credentials before logging or transmitting code to Gemini.

### Workflow D: GitHub Push Monitoring via Webhooks
- Independent FastAPI webhook server (`api.py`) running on port 8000.
- HMAC-SHA256 signature verification (`X-Hub-Signature-256`) using configured `WEBHOOK_SECRET`.
- Duplicate delivery prevention (`X-GitHub-Delivery`).
- Background job processing: downloads changed files, executes static checks + Gemini review, and stores results directly in SQLite.

### Workflow E: Longitudinal Review Tracking & Commit Comparison
- Tracks code quality scores, critical findings, and analysis duration over time.
- Interactive Plotly visualizations: quality trend progression, severity donut charts, repository health radar, and issues per repository.
- Commit comparison: identifies newly introduced vs resolved findings and score delta.

### Workflow F: Offline-Only Mode
- Full deterministic static analysis, McCabe complexity, and report generation operate 100% offline without sending any code externally when Gemini is disabled.

---

## 3. Technology Stack

- **Frontend:** Streamlit 1.40+ (Dark Developer Space Theme: `#0B1020`, Electric Blue `#4FD1E8`, Violet `#9D7BFF`)
- **Backend:** Python 3.10+
- **REST & Webhook Engine:** FastAPI + Uvicorn
- **AI Reasoning:** Google Gemini API using the official `google-genai` SDK (default: `gemini-2.5-flash`)
- **Static Analysis:** Python `ast`, `tokenize`, `compile()`, Radon, Lizard, Tree-Sitter (`tree-sitter-cpp`, `tree-sitter-java`)
- **Data Persistence:** SQLite (`techspec.db`) with clean repository pattern
- **Visualizations:** Plotly Express & Plotly Graph Objects
- **Testing:** Pytest (137 automated unit and integration tests)

---

## 4. Installation & Local Setup

### Step 1: Clone and Install Dependencies

```bash
cd TechSpecAnalyser
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Configure the following variables in `.env`:

```dotenv
# Required for AI review and codebase chat:
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Optional: For private GitHub repos & 5,000 req/hr rate limits:
GITHUB_TOKEN=your_github_personal_access_token_here

# Required for GitHub Webhooks:
WEBHOOK_SECRET=your_secure_webhook_secret_key_here
```

---

## 5. Running the Application

### 1. Launch Primary Streamlit Workbench

```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 2. Launch Webhook & REST API Service (Optional / Automation)

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```
Open API docs at `http://localhost:8000/docs`.

> **Note:** Both services can run concurrently. Streamlit provides the developer workbench, while FastAPI handles automated GitHub push webhooks in the background.

---

## 6. GitHub Webhook Configuration

To receive automatic reviews on every commit push:

1. Start the webhook server:
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000
   ```
2. In development, expose port 8000 using a secure tunnel (e.g. `ngrok` or `smee.io`):
   ```bash
   ngrok http 8000
   ```
3. In your GitHub repository:
   - Go to **Settings** → **Webhooks** → **Add Webhook**
   - **Payload URL:** `https://<your-ngrok-domain>/webhooks/github`
   - **Content type:** `application/json`
   - **Secret:** Enter the secret configured in `WEBHOOK_SECRET`
   - **Events:** Select **Just the push event**
   - Click **Add Webhook**.
4. Every push will automatically appear in your **Review History** and **Dashboard**!

---

## 7. Running the Automated Test Suite

Run the full automated test suite:

```bash
pytest -q
```

All 137 tests execute with mocks and fixtures, requiring zero Gemini credits and no live network dependencies:
- Multi-language AST, CST, and compiler syntax parsing
- CWE security rules and secret redactions
- 4-pillar transparent scoring engine
- GitHub fetcher safeguards and per-file failure isolation
- HMAC-SHA256 signature verification and push payload parsing
- SQLite persistence, genuine metrics, and session comparison
- Markdown, JSON, and CSV report export formats

---

## 8. Project Structure

```text
TechSpecAnalyser/
├── app.py                      # Main Streamlit application
├── api.py                      # FastAPI Webhook and REST API service
├── config.py                   # Central configuration & env management
│
├── core/
│   ├── reviewer.py             # Review pipeline coordinator
│   ├── gemini_client.py        # Google GenAI client, rate limits, quota circuit breaker
│   ├── review_orchestrator.py  # Single-file & multi-file coordination
│   ├── repository_intelligence.py # Grounded architecture, endpoints, models & docs
│   ├── scoring.py              # 4-pillar transparent scoring engine
│   └── security_redactor.py    # Pattern-based secret redactor
│
├── analyzers/
│   ├── base_analyzer.py        # Abstract base language adapter
│   ├── python_analyzer.py      # Python AST, imports, arities, leaks
│   ├── cpp_analyzer.py         # C/C++ compiler gate, leaks, tree-sitter
│   ├── java_analyzer.py        # Java class enclosure, tree-sitter, equality
│   ├── javascript_analyzer.py  # JS & JSX loose equality, debugger, DOM
│   ├── typescript_analyzer.py  # TS & TSX type suppression, any type
│   ├── web_analyzer.py         # HTML/CSS accessibility, deprecated tags
│   ├── static_analysis.py      # Multi-language dispatch
│   ├── syntax_checker.py       # Syntax validation across languages
│   ├── security_analyzer.py    # Dedicated multi-language CWE security engine
│   └── complexity.py           # Radon McCabe CC, Halstead MI, Lizard
│
├── integrations/
│   ├── github_client.py        # GitHub REST API client & rate limits
│   ├── github_fetcher.py       # Tree fetcher, size & file limits, isolation
│   ├── github_webhooks.py      # HMAC-SHA256 verification & push parser
│   └── github_reports.py       # PR comment & status reports
│
├── assistant/
│   ├── codebase_assistant.py   # Grounded codebase AI conversational agent
│   └── context_builder.py      # Context retriever with file & finding links
│
├── database/
│   ├── db.py                   # SQLite connection manager & schema migrations
│   └── repositories.py         # Query layer: sessions, metrics, webhooks, chats
│
├── reports/
│   ├── markdown_report.py      # Markdown report exporter
│   ├── json_report.py          # JSON export
│   └── export.py               # Unified diff, HTML, CSV exports
│
├── views/
│   ├── dashboard_view.py       # Developer space dashboard with live metrics
│   ├── review_view.py          # Code review (Paste & Repo) with tabs & diff
│   ├── intelligence_view.py    # Grounded architecture & generated docs
│   ├── security_view.py        # Security centre with CWE audit & secret scanner
│   ├── assistant_view.py       # AI assistant chat grounded in codebase
│   ├── history_view.py         # Review history & commit comparison
│   ├── analytics_view.py       # Longitudinal performance trends
│   ├── projects_view.py        # Tracked GitHub repositories
│   ├── add_repo_view.py        # Connect repository workflow
│   └── settings_view.py        # API keys & webhook configuration
│
├── components/
│   ├── styles.py               # Space-theme CSS design system
│   ├── charts.py               # Plotly interactive graphs
│   ├── finding_cards.py        # Actionable finding cards with AI fix buttons
│   └── code_diff.py            # Side-by-side and unified diff renderers
│
├── tests/                      # 137 automated unit and integration tests
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── .env.example                # Environment variable template
├── .gitignore                  # Git ignore rules
└── README.md                   # Full platform documentation
```

---

## 9. Privacy, Security & Safeguards

1. **Zero Secret Leaks:** All API keys, passwords, AWS tokens, and JWTs are automatically stripped via `security_redactor.py` before any data is logged, transmitted, or exported.
2. **Offline-First:** In offline mode, no source code ever leaves the local machine.
3. **No Execution of Untrusted Code:** TechSpecAnalyser statically parses source code via Abstract Syntax Trees; it never executes foreign code submitted for review.
4. **Fault-Isolated:** File-level error boundaries ensure an unparsable file never halts the review of remaining modules.
