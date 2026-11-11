"""
TechSpecAnalyser — Database Persistence & Repository Layer Test Suite.
Tests review session saving, genuine dashboard metrics, comparisons, and chat storage.
"""
from pathlib import Path
import tempfile
import pytest

from database.repositories import (
    compare_two_sessions,
    get_chat_history,
    get_dashboard_metrics,
    get_recent_sessions,
    get_session_by_id,
    save_chat_message,
    save_review_session,
)


def test_database_session_persistence_roundtrip(tmp_path):
    test_db = tmp_path / "test_techspec.db"

    session_record = {
        "id": "run-test-01",
        "repo_full_name": "developer/sample-repo",
        "branch": "main",
        "commit_sha": "a1b2c3d",
        "overall_score": 8.7,
        "critical_count": 0,
        "warning_count": 2,
        "files_analyzed": 5,
        "summary": "Clean architecture with minor style suggestions.",
        "bugs": [
            {"file": "app.py", "line": 10, "severity": "warning", "description": "Unused variable", "source": "static"}
        ],
        "security_findings": [],
    }

    sid = save_review_session(session_record, db_path=test_db)
    assert sid == "run-test-01"

    # Load recent
    sessions = get_recent_sessions(limit=10, db_path=test_db)
    assert len(sessions) == 1
    assert sessions[0]["id"] == "run-test-01"
    assert sessions[0]["repo_full_name"] == "developer/sample-repo"

    # Get by ID
    loaded = get_session_by_id("run-test-01", db_path=test_db)
    assert loaded is not None
    assert loaded["overall_score"] == 8.7


def test_dashboard_metrics_computed_from_database(tmp_path):
    test_db = tmp_path / "test_techspec_metrics.db"

    # Record 1
    save_review_session({
        "id": "run-01",
        "repo_full_name": "org/repo-a",
        "overall_score": 9.0,
        "files_analyzed": 4,
        "critical_count": 0,
        "bugs": [],
        "security_findings": [],
    }, db_path=test_db)

    # Record 2 with a critical finding
    save_review_session({
        "id": "run-02",
        "repo_full_name": "org/repo-b",
        "overall_score": 6.0,
        "files_analyzed": 6,
        "critical_count": 1,
        "bugs": [],
        "security_findings": [
            {"file": "auth.py", "line": 5, "severity": "critical", "cwe": "CWE-89", "title": "SQLi"}
        ],
    }, db_path=test_db)

    metrics = get_dashboard_metrics(db_path=test_db)
    assert metrics["connected_repositories"] == 2
    assert metrics["total_sessions"] == 2
    assert metrics["total_files_reviewed"] == 10
    assert metrics["average_quality_score"] == 7.5
    assert metrics["critical_security_vulnerabilities"] == 1


def test_session_comparison(tmp_path):
    test_db = tmp_path / "test_techspec_comp.db"

    save_review_session({
        "id": "run-v1",
        "repo_full_name": "org/app",
        "overall_score": 7.0,
        "bugs": [
            {"file": "app.py", "line": 10, "rule": "unused-var", "description": "var x unused"}
        ],
        "security_findings": [],
    }, db_path=test_db)

    save_review_session({
        "id": "run-v2",
        "repo_full_name": "org/app",
        "overall_score": 9.0,
        "bugs": [],  # fixed the unused var
        "security_findings": [],
    }, db_path=test_db)

    comp = compare_two_sessions("run-v1", "run-v2", db_path=test_db)
    assert comp["score_delta"] == 2.0
    assert comp["resolved_count"] == 1
    assert comp["new_count"] == 0


def test_assistant_chat_persistence(tmp_path):
    test_db = tmp_path / "test_techspec_chat.db"

    save_chat_message("org/app", "user", "How does auth work?", db_path=test_db)
    save_chat_message("org/app", "assistant", "Auth uses JWT tokens.", db_path=test_db)

    history = get_chat_history("org/app", db_path=test_db)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
