"""
TechSpecAnalyser — Repository Intelligence & Documentation Test Suite.
Tests grounded architecture deduction, endpoint parsing, and documentation generation.
"""
from core.repository_intelligence import RepositoryIntelligenceEngine


def test_repository_intelligence_analysis():
    engine = RepositoryIntelligenceEngine()

    files = [
        {
            "path": "app.py",
            "content": """
import os
from fastapi import FastAPI
app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL")

@app.get("/api/users")
def get_users():
    return [{"id": 1, "name": "Alice"}]
""",
            "language": "Python",
        },
        {
            "path": "models.py",
            "content": """
from sqlalchemy.orm import declarative_base
Base = declarative_base()

class UserModel(Base):
    __tablename__ = "users"
""",
            "language": "Python",
        },
        {
            "path": "src/App.tsx",
            "content": """
import React from 'react';
export const App = () => <h1>TechSpecAnalyser Workbench</h1>;
""",
            "language": "TSX",
        },
    ]

    report = engine.analyze_repository(files, project_name="FullStackPlatform")

    assert report["total_files"] == 3
    assert report["primary_language"] == "Python"
    assert "FastAPI" in report["detected_frameworks"]
    assert "React" in report["detected_frameworks"]

    # Endpoints
    eps = report["detected_endpoints"]
    assert len(eps) >= 1
    assert eps[0]["method"] == "GET"
    assert eps[0]["path"] == "/api/users"

    # Models
    models = report["detected_models"]
    assert len(models) >= 1
    assert models[0]["name"] == "UserModel"

    # Environment variables
    assert "DATABASE_URL" in report["env_vars_referenced"]

    # Documentation content
    doc = report["documentation"]
    assert "# FullStackPlatform" in doc
    assert "FastAPI" in doc
    assert "/api/users" in doc
    assert "DATABASE_URL" in doc
