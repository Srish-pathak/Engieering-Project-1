# ⚡ TechSpecAnalyser
### Don't Just Write Code. Understand It. Secure It. Improve It.

<p align="center">
  <strong>AI-Powered Code Intelligence, Security & Repository Analysis Platform</strong><br/>
  Intelligent Code Review · Vulnerability Detection · Repository Intelligence · AI Assistance
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Developer%20Tool-blueviolet?style=for-the-badge" />
  <img src="https://img.shields.io/badge/AI-Google%20Gemini-4285F4?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Database-SQLite-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Testing-137%20Tests-success?style=for-the-badge" />
</p>

---

## 💡 The Story Behind TechSpecAnalyser

Imagine this:

It's 2:00 AM. You're working on a software project. Your application has hundreds of lines of code, multiple dependencies, and several interconnected modules.

Everything seems to work.

But somewhere inside your code, there could be:

- A hidden security vulnerability.
- An inefficient algorithm.
- An undefined variable.
- A hardcoded API key.
- A function with unnecessarily high complexity.
- A bug waiting to appear in production.

Now imagine having to manually inspect every file to find these problems.

**Wouldn't it be better if your code could explain its own problems?**

That's exactly the idea behind **TechSpecAnalyser!**

TechSpecAnalyser is an intelligent software engineering platform that combines traditional static code analysis with Google Gemini AI to inspect source code, identify vulnerabilities, understand repositories, and suggest meaningful improvements.

Our idea is simple:

**Less debugging guesswork. Better code quality. Stronger software security.**

---

## 🎯 What Are We Trying to Achieve?

TechSpecAnalyser aims to make software development more intelligent, secure, and efficient.

1. **Automated Code Review:** Analyse source code and identify potential bugs and coding issues.
2. **Multi-Language Analysis:** Support code analysis across Python, C, C++, Java, JavaScript, TypeScript, HTML and CSS.
3. **Security Intelligence:** Detect common vulnerabilities and map them to CWE identifiers.
4. **Repository Understanding:** Analyse GitHub repositories and generate technical architecture documentation.
5. **AI-Powered Improvements:** Generate code suggestions, optimized versions and validated fixes.
6. **Continuous Monitoring:** Automatically review code changes through GitHub push webhooks.
7. **Code Quality Tracking:** Monitor quality scores, security findings and repository health over time.

---

## ✨ What Can TechSpecAnalyser Do?

| Feature | Description |
|---|---|
| 📝 Intelligent Code Review | Analyse pasted source code and uploaded files |
| 🌐 Multi-Language Support | Analyse Python, C, C++, Java, JS, TS, HTML and CSS |
| 🔍 Syntax Validation | Detect syntax errors before AI analysis |
| 🐛 Bug Detection | Identify common programming mistakes and code issues |
| 🛡️ Security Auditing | Detect vulnerabilities using CWE-mapped security rules |
| 🔐 Secret Redaction | Mask API keys, credentials and sensitive information |
| 📂 GitHub Repository Analysis | Inspect repository structure, branches and commits |
| 🧠 Repository Intelligence | Generate architecture insights and project documentation |
| 🤖 AI Code Assistant | Ask questions about your codebase |
| ⚡ AI-Powered Code Fixes | Generate improved code with side-by-side diffs |
| 📡 GitHub Webhook Monitoring | Trigger automated reviews after repository pushes |
| 📊 Quality Analytics | Visualize code quality and security trends |
| 📜 Review History | Track previous reviews and compare commits |
| 📥 Report Export | Export findings in Markdown, JSON and CSV |
| 🔌 Offline Analysis | Perform deterministic static analysis without Gemini |

---

## 🏗️ System Architecture

TechSpecAnalyser combines deterministic program analysis, AI reasoning, repository integration and persistent storage into one unified workflow.

```text
                     👨‍💻 USER / DEVELOPER
                              |
               +--------------+--------------+
               |                             |
               ▼                             ▼
       STREAMLIT WORKBENCH             FASTAPI SERVICE
               |                             |
       +-------+--------+              GITHUB WEBHOOKS
       |       |        |                     |
       ▼       ▼        ▼                     ▼
     PASTE   FILE    GITHUB              PUSH EVENTS
     CODE   UPLOAD   REPOSITORY                |
       |       |        |                     |
       +-------+--------+---------------------+
                              |
                              ▼
                  MULTI-LANGUAGE DISPATCHER
                              |
          +-------------------+-------------------+
          |         |         |         |         |
          ▼         ▼         ▼         ▼         ▼
        Python    C/C++     Java       JS/TS     HTML/CSS
          |         |         |         |         |
          +---------+---------+---------+---------+
                              |
                              ▼
                    STATIC ANALYSIS ENGINE
                              |
                              ▼
                   SECURITY ANALYSIS ENGINE
                              |
                              ▼
                      SECRET REDACTION
                              |
                              ▼
                    GOOGLE GEMINI AI
                              |
                              ▼
                  4-PILLAR QUALITY SCORING
                              |
                              ▼
                       SQLITE DATABASE
                              |
              +---------------+---------------+
              |               |               |
              ▼               ▼               ▼
          DASHBOARD       REPORTS         ANALYTICS
              |
              ▼
         CODE INSIGHTS
```

### 🔄 How Does It Work?

1. The user submits source code, uploads files or connects a GitHub repository.
2. The analysis dispatcher identifies the programming language.
3. Static analyzers validate syntax and inspect code structures.
4. The security engine checks for known vulnerability patterns.
5. Sensitive information is redacted before AI processing.
6. Google Gemini provides additional reasoning and improvement suggestions.
7. The scoring engine calculates an overall code quality score.
8. Results are stored in SQLite and displayed through the Streamlit dashboard.

---

## 🛡️ Security Intelligence

Security is one of the most important parts of TechSpecAnalyser.

The dedicated security engine identifies common vulnerability patterns and associates them with Common Weakness Enumeration (CWE) identifiers.

| Vulnerability | CWE |
|---|---|
| Hardcoded Credentials | CWE-798 |
| SQL Injection | CWE-89 |
| OS Command Injection | CWE-78 |
| Unsafe Deserialization | CWE-502 |
| Cross-Site Scripting (XSS) | CWE-79 |
| Path Traversal | CWE-22 |
| Weak Cryptographic Algorithms | CWE-327 |
| Disabled SSL Verification | CWE-295 |
| Permissive CORS Configuration | CWE-942 |
| Buffer Overflow Patterns | CWE-120 |

### 🔐 Secret Protection

Before source code is transmitted to Gemini or included in logs and exports, the security redaction layer masks detected credentials and sensitive values.

The platform also supports offline-only analysis when Gemini is disabled.

---

## 📊 Transparent Code Quality Scoring

TechSpecAnalyser uses a four-pillar scoring model to evaluate code quality.

| Quality Pillar | Weight |
|---|---:|
| 🛡️ Security | 30% |
| 🐛 Bugs | 30% |
| 🧩 Maintainability Index | 20% |
| ⚙️ Cyclomatic Complexity | 20% |
| **Total** | **100%** |

This approach combines security, correctness and maintainability instead of evaluating code using a single metric.

---

## 🧠 AI-Powered Repository Intelligence

Why analyse individual files when you can understand an entire repository?

TechSpecAnalyser connects with GitHub repositories and extracts useful technical information.

- Explore repository branches and commit history.
- Inspect directory structures and source files.
- Analyse multiple files with fault isolation.
- Generate technical architecture reports.
- Understand application components and relationships.
- Generate `PROJECT_DOCUMENTATION.md`.
- Compare findings across different commits.

---

## 🤖 Your AI Codebase Assistant

Imagine asking your repository:

- What does this project actually do?
- Which module handles authentication?
- Where are the potential security risks?
- How does the backend communicate with the frontend?
- Which functions should be optimized?

The integrated AI codebase assistant helps developers investigate their repositories through conversational questions grounded in repository context.

---

## 📡 Automated GitHub Monitoring

TechSpecAnalyser also supports automated code reviews through GitHub push webhooks.

### Workflow

1. Configure a GitHub webhook.
2. A developer pushes new code.
3. GitHub sends a push event to the FastAPI service.
4. The server verifies the HMAC-SHA256 signature.
5. Changed files are retrieved and analysed.
6. Static checks and Gemini review are performed.
7. Results are saved in SQLite.
8. Developers can inspect the review history and dashboard.

This makes continuous code quality monitoring possible without manually starting every review.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Streamlit 1.40+ |
| Backend | Python 3.10+ |
| API Framework | FastAPI, Uvicorn |
| AI Engine | Google Gemini 2.5 Flash |
| Code Parsing | Python AST, Tokenize, Tree-Sitter |
| Complexity Analysis | Radon, Lizard |
| Static Analysis | Custom Multi-Language Analyzers |
| Security | CWE-Based Static Security Engine |
| Database | SQLite |
| Visualization | Plotly |
| Repository Integration | GitHub REST API |
| Webhook Security | HMAC-SHA256 |
| Testing | Pytest |

---

## 📂 Project Structure

```text
TechSpecAnalyser/
│
├── app.py
├── api.py
├── config.py
│
├── core/
│   ├── reviewer.py
│   ├── gemini_client.py
│   ├── review_orchestrator.py
│   ├── repository_intelligence.py
│   ├── scoring.py
│   └── security_redactor.py
│
├── analyzers/
│   ├── base_analyzer.py
│   ├── python_analyzer.py
│   ├── cpp_analyzer.py
│   ├── java_analyzer.py
│   ├── javascript_analyzer.py
│   ├── typescript_analyzer.py
│   ├── web_analyzer.py
│   ├── static_analysis.py
│   ├── syntax_checker.py
│   ├── security_analyzer.py
│   └── complexity.py
│
├── integrations/
│   ├── github_client.py
│   ├── github_fetcher.py
│   ├── github_webhooks.py
│   └── github_reports.py
│
├── assistant/
│   ├── codebase_assistant.py
│   └── context_builder.py
│
├── database/
│   ├── db.py
│   └── repositories.py
│
├── reports/
│   ├── markdown_report.py
│   ├── json_report.py
│   └── export.py
│
├── views/
│   ├── dashboard_view.py
│   ├── review_view.py
│   ├── intelligence_view.py
│   ├── security_view.py
│   ├── assistant_view.py
│   ├── history_view.py
│   ├── analytics_view.py
│   ├── projects_view.py
│   ├── add_repo_view.py
│   └── settings_view.py
│
├── components/
│   ├── styles.py
│   ├── charts.py
│   ├── finding_cards.py
│   └── code_diff.py
│
├── tests/
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/TechSpecAnalyser.git

cd TechSpecAnalyser
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and configure:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

GITHUB_TOKEN=your_github_token

WEBHOOK_SECRET=your_webhook_secret
```

Keep your `.env` file private. Never commit API keys or credentials to GitHub.

### 4. Launch the Application

Start the Streamlit workbench:

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

### 5. Launch the FastAPI Service

For webhook automation:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

API documentation:

```text
http://localhost:8000/docs
```

---

## 🧪 Automated Testing

Quality matters, especially when building a platform that analyses other people's code.

TechSpecAnalyser includes **137 automated unit and integration tests**.

Run the test suite:

```bash
pytest -q
```

The tests cover:

- Multi-language syntax and static analysis.
- Security vulnerability detection.
- Secret redaction.
- Four-pillar scoring.
- GitHub repository fetching safeguards.
- Webhook signature verification.
- SQLite persistence.
- Review history and commit comparison.
- Markdown, JSON and CSV report generation.

The test suite uses mocks and fixtures, requiring no live Gemini API credits or network dependencies.

---

## 🔒 Privacy, Security & Reliability

TechSpecAnalyser follows several important design principles:

1. **Secret Protection:** Sensitive credentials are masked before logging, transmitting or exporting source code.
2. **Offline-First Analysis:** Deterministic analysis can operate without external AI services.
3. **No Execution of Untrusted Code:** Source code is analysed statically rather than executed.
4. **Fault Isolation:** A problematic file does not stop the analysis of the remaining repository.
5. **Repository Safeguards:** File-size limits and directory exclusions help control repository analysis.

---

## 🔮 What's Next? — Future Scope

TechSpecAnalyser is designed with room for further development.

Possible enhancements include:

- Pull request review automation.
- Additional programming language support.
- Advanced vulnerability detection.
- Dependency vulnerability analysis.
- Deeper semantic code understanding.
- More advanced AI-assisted refactoring.
- Team-based code quality analytics.
- IDE integration and real-time feedback.

---

## 🌟 Our Vision

We believe that good software development is not just about writing code that works.

It is about writing code that is secure, maintainable, understandable and reliable.

Developers should spend less time searching for hidden bugs and more time building meaningful solutions.

TechSpecAnalyser brings traditional software engineering techniques and modern AI reasoning together to make that possible.

**Because better software starts with better understanding.**

<p align="center">
  <strong>⚡ TechSpecAnalyser</strong><br/>
  <em>Analyse Smarter. Code Better. Build Securely.</em>
</p>

---

<p align="center">
  Built with Python, AI and a passion for better software engineering.
</p>
