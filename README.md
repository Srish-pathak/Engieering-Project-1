# TechSpecAnalyser

TechSpecAnalyser is a web app for reviewing source code and small repositories. It combines deterministic static analysis with optional Google Gemini review, then presents findings, complexity metrics, documentation, and downloadable reports.

The runnable app is a React/Vite frontend served by an Express server. The server calls a Python analysis engine. The repository also contains an older Streamlit/FastAPI implementation; the Dockerfile and current web entry point use the React/Express app.

## Features

- Review pasted Python code or upload source files and ZIP archives.
- Import a GitHub repository by URL and optionally choose a branch.
- Detect syntax issues, common bugs, security patterns, and maintainability concerns.
- Measure cyclomatic complexity and Python maintainability metrics.
- Generate AST-based project documentation and architecture summaries.
- Add optional Gemini review, recommendations, and suggested code improvements.
- View review history and evaluation results, and export reports.

Analysis is available without Gemini. Gemini adds AI-generated review and recommendations when a key is configured.

## Supported languages

The current analysis engine supports **Python, C++, and Java**. For repository imports and ZIP uploads, it recognizes these source extensions:

- Python: `.py`
- C++: `.cpp`, `.cc`, `.cxx`, `.hpp`, `.h`
- Java: `.java`

Repository archives are limited to 10 MB and up to 80 supported source files. Other files are skipped.

## Requirements

- Node.js 22 (the version used by the Docker image)
- Python 3 with pip
- A Google Gemini API key for AI features (optional)
- A GitHub token for private repositories or higher GitHub API limits (optional)

## Run locally

1. Install dependencies:

   ```bash
   npm install
   python3 -m pip install -r requirements.txt
   ```

2. Optionally create a `.env` file in the project root:

   ```env
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL=your_supported_gemini_model
   GITHUB_TOKEN=your_github_token
   ```

   Leave `GEMINI_API_KEY` unset to use deterministic analysis without AI. `GITHUB_TOKEN` is only needed for private repositories or to reduce unauthenticated API rate-limit issues. Keep `.env` private; it is ignored by Git.

3. Start the app:

   ```bash
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000). The Express server starts Vite for the frontend and exposes the analysis API.

For a production-style local run, build the frontend and start the server:

```bash
npm run build
npm start
```

## Run with Docker

The Dockerfile installs Node.js 22, Python, Node dependencies, and Python requirements, builds the frontend, and starts the Express server on port 3000.

```bash
docker build -t techspecanalyser .
docker run --rm -p 3000:3000 --env-file .env techspecanalyser
```

The `.env` file is optional when using deterministic analysis only.

## Import a GitHub repository

1. Open **GitHub Repository** in the app.
2. Enter a repository URL such as `https://github.com/owner/repository`.
3. Optionally enter a branch. Leave it blank to use the repository's default branch.
4. Start the analysis.

The server downloads the repository archive from GitHub, filters it to supported source files, and sends those files through the same analysis pipeline used for uploaded projects. Public repositories work without a token, subject to GitHub's unauthenticated rate limits. Set `GITHUB_TOKEN` for private repository access.

## Useful commands

```bash
npm run dev      # Start the app for development
npm run build    # Build the frontend
npm start        # Start the server
npm test         # Run the backend test suite
npm run lint     # Type-check the TypeScript
```

## Main project areas

- `src/`: React interface and sample projects
- `server.ts`: Express server, GitHub import, Gemini orchestration, and API routes
- `backend/codelens_engine.py`: Python static analysis, metrics, documentation, ZIP validation, and history
- `backend/tests/`: Python backend tests

