"""
TechSpecAnalyser — SQLite Database Connection & Schema Management.
Ensures reliable transaction handling and clean connection teardown
preventing Windows file-locking issues.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from config import DB_PATH

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    repo_url TEXT,
    default_branch TEXT DEFAULT 'main',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    repo_full_name TEXT NOT NULL,
    branch TEXT NOT NULL,
    commit_sha TEXT,
    input_mode TEXT NOT NULL,
    overall_score REAL NOT NULL,
    security_score REAL NOT NULL,
    correctness_score REAL NOT NULL,
    maintainability_score REAL NOT NULL,
    complexity_score REAL NOT NULL,
    files_analyzed INTEGER NOT NULL DEFAULT 1,
    critical_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    info_count INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    severity TEXT NOT NULL,
    category TEXT NOT NULL,
    rule_id TEXT,
    cwe_id TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT DEFAULT 'high',
    FOREIGN KEY (session_id) REFERENCES review_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS webhook_events (
    delivery_id TEXT PRIMARY KEY,
    repo_full_name TEXT NOT NULL,
    branch TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assistant_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    repo_full_name TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_repo ON review_sessions(repo_full_name);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON review_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_findings_session ON findings(session_id);
"""


def init_db(db_path: Path = DB_PATH) -> None:
    """Initializes tables and indexes if they do not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db_connection(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager yielding a sqlite3 connection with row_factory=Row.
    Guarantees connection is closed when the block exits.
    """
    init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
