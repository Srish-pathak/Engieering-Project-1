"""
TechSpecAnalyser — Central Configuration and Environment Management.
Supports .env, environment variables, and Streamlit secrets.
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load local .env if present
load_dotenv()

# Base project directory
BASE_DIR = Path(__file__).resolve().parent

# Application Metadata
APP_NAME = "TechSpecAnalyser"
APP_TAGLINE = "Your Intelligent AI-Powered Code Review, Security & Repository Intelligence Platform"
APP_VERSION = "2.0.0"

# AI Configuration
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_CODE_CHARS = int(os.getenv("MAX_CODE_CHARS", "25000"))
AI_MAX_ATTEMPTS = int(os.getenv("AI_MAX_ATTEMPTS", "3"))
AI_RETRY_DELAY = float(os.getenv("AI_RETRY_DELAY", "2.0"))

# GitHub Integration Configuration
DEFAULT_MAX_REPO_FILES = int(os.getenv("MAX_REPO_FILES", "30"))
DEFAULT_MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(200 * 1024)))  # 200 KB
GITHUB_API_BASE = "https://api.github.com"

# Webhook Configuration
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "techspec-webhook-secret-key")

# Database Configuration
DEFAULT_DB_PATH = BASE_DIR / "techspec.db"
DB_PATH = Path(os.getenv("TECHSPEC_DB_PATH", str(DEFAULT_DB_PATH)))

# Supported Languages and File Extensions
LANGUAGE_EXTENSIONS = {
    "Python": [".py"],
    "C": [".c", ".h"],
    "C++": [".cpp", ".cc", ".cxx", ".hpp"],
    "Java": [".java"],
    "JavaScript": [".js", ".mjs", ".cjs"],
    "JSX": [".jsx"],
    "TypeScript": [".ts"],
    "TSX": [".tsx"],
    "HTML": [".html", ".htm"],
    "CSS": [".css"],
    "SCSS": [".scss"],
}

EXTENSION_TO_LANGUAGE = {
    ext: lang for lang, exts in LANGUAGE_EXTENSIONS.items() for ext in exts
}

IGNORED_DIRECTORIES = {
    ".git", ".venv", "venv", "env", "__pycache__", "node_modules",
    "dist", "build", ".pytest_cache", ".mypy_cache", ".idea", ".vscode",
    "coverage", ".next", "target", "out", ".cargo", "vendor",
}

IGNORED_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".dll", ".so", ".dylib", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".zip", ".tar", ".gz",
    ".pdf", ".lock", ".db", ".sqlite", ".sqlite3",
}


def get_gemini_api_key(override_key: Optional[str] = None) -> str:
    """Retrieve Gemini API key with priority: sidebar override > env var > streamlit secrets."""
    if override_key and override_key.strip() and override_key.upper() not in ("YOUR_API_KEY", "YOUR_API_KEY_HERE"):
        return override_key.strip()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key and key.upper() not in ("YOUR_API_KEY", "YOUR_API_KEY_HERE"):
        return key
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            s_key = st.secrets["GEMINI_API_KEY"].strip()
            if s_key and s_key.upper() not in ("YOUR_API_KEY", "YOUR_API_KEY_HERE"):
                return s_key
    except Exception:
        pass
    return ""


def is_gemini_configured(override_key: Optional[str] = None) -> bool:
    """Check if a usable Gemini API key is available."""
    return bool(get_gemini_api_key(override_key))


def get_github_token(override_token: Optional[str] = None) -> str:
    """Retrieve GitHub token with priority: override > env var > streamlit secrets."""
    if override_token and override_token.strip():
        return override_token.strip()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets:
            return st.secrets["GITHUB_TOKEN"].strip()
    except Exception:
        pass
    return ""


def detect_language(file_path: str) -> str:
    """Detect programming language from file path extension."""
    suffix = Path(file_path).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(suffix, "Unknown")
