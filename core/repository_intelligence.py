"""
TechSpecAnalyser — Repository Intelligence & Grounded Architecture Analysis.
Extracts project intent, technology stacks, entry points, API endpoints,
database schemas, environment variables, and generates comprehensive
project documentation grounded in deterministic repository facts.
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from config import detect_language


class RepositoryIntelligenceEngine:
    """Extracts architectural intelligence and generates project documentation."""

    def __init__(self):
        pass

    def analyze_repository(
        self,
        files: List[Dict[str, Any]],
        project_name: str = "Repository",
    ) -> Dict[str, Any]:
        """
        Analyzes a set of files ({path, content, language}) and produces
        a comprehensive intelligence report.
        """
        total_files = len(files)
        total_loc = 0
        lang_stats: Dict[str, Dict[str, int]] = {}

        all_imports: Set[str] = set()
        detected_frameworks: Set[str] = set()
        detected_endpoints: List[Dict[str, str]] = []
        detected_models: List[Dict[str, str]] = []
        env_vars_referenced: Set[str] = set()
        entry_points: List[str] = []

        file_tree = []

        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            lang = f.get("language") or detect_language(path)

            file_tree.append(path)
            lines = content.splitlines()
            loc = len([l for l in lines if l.strip()])
            total_loc += loc

            # Language breakdown
            if lang not in lang_stats:
                lang_stats[lang] = {"files": 0, "loc": 0}
            lang_stats[lang]["files"] += 1
            lang_stats[lang]["loc"] += loc

            # Entry points detection
            base_name = Path(path).name.lower()
            if base_name in ("app.py", "main.py", "server.ts", "server.js", "index.ts", "index.js", "main.tsx", "index.html", "manage.py"):
                entry_points.append(path)

            # Environment variables referenced
            for m in re.finditer(r"""(?:\bos\.getenv\s*\(\s*['"]|\bos\.environ\.get\s*\(\s*['"]|\bos\.environ\[['"]|process\.env\.)([A-Za-z0-9_]+)""", content):
                env_vars_referenced.add(m.group(1))

            # API Endpoints detection (FastAPI, Flask, Express, etc.)
            for idx, line in enumerate(lines, 1):
                # Python @app.get('/path') or @router.post(...)
                ep_py = re.search(r"""@(?:app|router|api)\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]""", line)
                if ep_py:
                    detected_endpoints.append({
                        "method": ep_py.group(1).upper(),
                        "path": ep_py.group(2),
                        "file": path,
                        "line": str(idx),
                    })
                # Express app.get('/path', ...) or router.post(...)
                ep_js = re.search(r"""(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]""", line)
                if ep_js:
                    detected_endpoints.append({
                        "method": ep_js.group(1).upper(),
                        "path": ep_js.group(2),
                        "file": path,
                        "line": str(idx),
                    })

            # Database Models & Schemas
            for idx, line in enumerate(lines, 1):
                # Python SQLAlchemy / Django / Pydantic
                model_py = re.search(r"""class\s+([A-Za-z0-9_]+)\s*\(\s*(?:Base|models\.Model|db\.Model|BaseModel)\s*\):""", line)
                if model_py:
                    detected_models.append({
                        "name": model_py.group(1),
                        "file": path,
                        "line": str(idx),
                    })

            # Framework detection from imports
            if lang == "Python":
                if "import streamlit" in content or "from streamlit" in content:
                    detected_frameworks.add("Streamlit")
                if "import fastapi" in content or "from fastapi" in content:
                    detected_frameworks.add("FastAPI")
                if "import flask" in content or "from flask" in content:
                    detected_frameworks.add("Flask")
                if "import django" in content or "from django" in content:
                    detected_frameworks.add("Django")
                if "import torch" in content or "import tensorflow" in content:
                    detected_frameworks.add("Deep Learning (PyTorch/TensorFlow)")
                if "from google import genai" in content or "import google.generativeai" in content:
                    detected_frameworks.add("Google Gemini GenAI SDK")
                if "import sqlite3" in content:
                    detected_frameworks.add("SQLite")
                if "import sqlalchemy" in content:
                    detected_frameworks.add("SQLAlchemy ORM")

            elif lang in ("JavaScript", "TypeScript", "JSX", "TSX"):
                if "from 'react'" in content or 'from "react"' in content:
                    detected_frameworks.add("React")
                if "from 'express'" in content or 'from "express"' in content:
                    detected_frameworks.add("Express.js")
                if "from 'next'" in content or 'from "next"' in content:
                    detected_frameworks.add("Next.js")
                if "from 'vite'" in content or 'from "vite"' in content:
                    detected_frameworks.add("Vite")
                if "tailwindcss" in content:
                    detected_frameworks.add("Tailwind CSS")

        # Project summary deduction
        primary_lang = max(lang_stats.items(), key=lambda x: x[1]["loc"])[0] if lang_stats else "Unknown"

        # Generate overview text
        overview = self._build_overview(
            project_name, primary_lang, total_files, total_loc, detected_frameworks, entry_points
        )

        # Technical architecture
        architecture = self._build_architecture(
            detected_frameworks, entry_points, detected_endpoints, detected_models, env_vars_referenced
        )

        # Project documentation
        documentation = self.generate_project_documentation(
            project_name=project_name,
            overview=overview,
            architecture=architecture,
            lang_stats=lang_stats,
            entry_points=entry_points,
            endpoints=detected_endpoints,
            models=detected_models,
            env_vars=sorted(env_vars_referenced),
            files=file_tree,
        )

        return {
            "project_name": project_name,
            "total_files": total_files,
            "total_loc": total_loc,
            "primary_language": primary_lang,
            "language_breakdown": lang_stats,
            "detected_frameworks": sorted(detected_frameworks),
            "entry_points": entry_points,
            "detected_endpoints": detected_endpoints,
            "detected_models": detected_models,
            "env_vars_referenced": sorted(env_vars_referenced),
            "overview": overview,
            "architecture": architecture,
            "documentation": documentation,
        }

    def _build_overview(
        self,
        name: str,
        primary_lang: str,
        files_count: int,
        loc: int,
        frameworks: Set[str],
        entry_points: List[str],
    ) -> Dict[str, Any]:
        fw_str = ", ".join(sorted(frameworks)) if frameworks else "standard library modules"
        return {
            "summary": (
                f"`{name}` is a software project comprising {files_count} analyzed file(s) and {loc:,} lines of code, "
                f"built primarily in {primary_lang}. The project utilizes {fw_str}."
            ),
            "primary_purpose": f"Software application built in {primary_lang} with key entry points: {', '.join(entry_points) or 'modular library'}.",
            "target_audience": "Developers and end-users interacting with the service or platform.",
            "tech_stack": list(frameworks) + [primary_lang],
        }

    def _build_architecture(
        self,
        frameworks: Set[str],
        entry_points: List[str],
        endpoints: List[Dict[str, str]],
        models: List[Dict[str, str]],
        env_vars: Set[str],
    ) -> Dict[str, Any]:
        has_frontend = any(f in frameworks for f in ("React", "Streamlit", "Next.js", "Vite"))
        has_backend = any(f in frameworks for f in ("FastAPI", "Flask", "Django", "Express.js"))
        has_database = any(f in frameworks for f in ("SQLite", "SQLAlchemy ORM")) or bool(models)

        return {
            "pattern": "Multi-Tier Web Architecture" if (has_frontend and has_backend) else "Single-Tier / Modular Library",
            "frontend": "Web UI detected (" + ", ".join([f for f in frameworks if f in ("React", "Streamlit", "Next.js", "Vite")]) + ")" if has_frontend else "Command-line or Headless Backend",
            "backend": "REST / Application Server (" + ", ".join([f for f in frameworks if f in ("FastAPI", "Flask", "Django", "Express.js")]) + ")" if has_backend else "Library Core Execution",
            "storage": f"Persistent storage with {len(models)} detected models/schemas." if has_database else "Stateless / in-memory or file-based persistence.",
            "api_endpoint_count": len(endpoints),
            "database_model_count": len(models),
            "env_var_count": len(env_vars),
        }

    def generate_project_documentation(
        self,
        project_name: str,
        overview: Dict[str, Any],
        architecture: Dict[str, Any],
        lang_stats: Dict[str, Any],
        entry_points: List[str],
        endpoints: List[Dict[str, str]],
        models: List[Dict[str, str]],
        env_vars: List[str],
        files: List[str],
    ) -> str:
        """Generates an informative, comprehensive Markdown project documentation."""
        doc_lines = [
            f"# {project_name} — Technical Specification & Documentation",
            "",
            "> *Generated by TechSpecAnalyser — Advanced Code Intelligence & Security Platform.*",
            "",
            "## 1. Project Introduction & Overview",
            overview.get("summary", ""),
            "",
            f"- **Primary Architecture Pattern:** {architecture.get('pattern', 'Modular')}",
            f"- **Frontend Component:** {architecture.get('frontend', 'N/A')}",
            f"- **Backend Component:** {architecture.get('backend', 'N/A')}",
            f"- **Data Storage Layer:** {architecture.get('storage', 'N/A')}",
            "",
            "## 2. Technology Stack & Language Distribution",
            "| Language | Files | Lines of Code |",
            "| :--- | :--- | :--- |",
        ]

        for lang, stats in lang_stats.items():
            doc_lines.append(f"| {lang} | {stats.get('files', 0)} | {stats.get('loc', 0):,} |")

        doc_lines.extend([
            "",
            "## 3. Key Application Entry Points",
            "\n".join(f"- `{ep}`" for ep in entry_points) if entry_points else "No standard entry file detected.",
            "",
            "## 4. API Endpoints",
        ])

        if endpoints:
            doc_lines.append("| Method | Endpoint Path | Source File | Line |")
            doc_lines.append("| :--- | :--- | :--- | :--- |")
            for ep in endpoints[:30]:
                doc_lines.append(f"| `{ep['method']}` | `{ep['path']}` | `{ep['file']}` | {ep['line']} |")
        else:
            doc_lines.append("No explicit HTTP REST endpoints detected in analyzed files.")

        doc_lines.extend([
            "",
            "## 5. Detected Database Models & Schemas",
        ])

        if models:
            doc_lines.append("| Model Name | Source File | Line |")
            doc_lines.append("| :--- | :--- | :--- |")
            for m in models:
                doc_lines.append(f"| `{m['name']}` | `{m['file']}` | {m['line']} |")
        else:
            doc_lines.append("No ORM schema classes or database model definitions detected.")

        doc_lines.extend([
            "",
            "## 6. Environment Variables Referenced",
            "\n".join(f"- `{ev}`" for ev in env_vars) if env_vars else "No direct environment variable access detected.",
            "",
            "## 7. File Directory Tree",
            "```text",
            "\n".join(files[:60]),
            "```" + ("\n*(truncated for brevity)*" if len(files) > 60 else ""),
            "",
            "## 8. Recommendations & Security Guidelines",
            "- Ensure all referenced environment variables are documented in a `.env.example` template.",
            "- Validate and sanitize all external user inputs at API boundary endpoints.",
            "- Maintain automated unit and static analysis coverage across all modified modules.",
        ])

        return "\n".join(doc_lines)
