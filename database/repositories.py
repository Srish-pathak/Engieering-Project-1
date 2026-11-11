"""
TechSpecAnalyser — Database Repository Access Layer.
Manages persistent records for review sessions, findings,
real dashboard metrics, webhook deliveries, and assistant chats.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DB_PATH
from database.db import get_db_connection


def save_review_session(
    record: Dict[str, Any],
    db_path: Path = DB_PATH,
) -> str:
    """
    Saves a complete review session and individual findings into SQLite.
    Returns session_id.
    """
    session_id = record.get("id") or f"run-{uuid.uuid4().hex[:10]}"
    project_id = record.get("project_id") or record.get("repo_full_name") or "default-project"
    repo_name = record.get("repo_full_name") or record.get("project_name") or "Local Workspace"
    branch = record.get("branch") or "main"
    commit_sha = record.get("commit_sha") or ""
    input_mode = record.get("input_mode") or "paste"
    now_str = record.get("time") or datetime.now().strftime("%d %b %Y, %H:%M")

    overall_score = float(record.get("overall_score", record.get("score", 0.0)))
    scores = record.get("scores") or {}
    security_score = float(scores.get("security_score", 10.0))
    correctness_score = float(scores.get("correctness_score", 10.0))
    maint_score = float(scores.get("maintainability_score", 10.0))
    comp_score = float(scores.get("complexity_score", 10.0))

    files_count = int(record.get("files_analyzed", 1))
    crit_count = int(record.get("critical", record.get("critical_count", 0)))
    warn_count = int(record.get("warning", record.get("warning_count", 0)))
    info_count = int(record.get("info", record.get("info_count", 0)))
    duration_ms = int(record.get("duration_ms", record.get("execution_ms", 0)))
    summary = record.get("summary", "")

    # Serialized full payload
    payload_json = json.dumps(record, ensure_ascii=False)

    with get_db_connection(db_path) as conn:
        # 1. Ensure project exists
        conn.execute(
            """
            INSERT OR REPLACE INTO projects (project_id, name, repo_url, default_branch, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project_id, repo_name, record.get("repo_url", ""), branch, now_str, now_str),
        )

        # 2. Insert review session
        conn.execute(
            """
            INSERT OR REPLACE INTO review_sessions (
                id, project_id, repo_full_name, branch, commit_sha, input_mode,
                overall_score, security_score, correctness_score, maintainability_score, complexity_score,
                files_analyzed, critical_count, warning_count, info_count,
                duration_ms, summary, created_at, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id, project_id, repo_name, branch, commit_sha, input_mode,
                overall_score, security_score, correctness_score, maint_score, comp_score,
                files_count, crit_count, warn_count, info_count,
                duration_ms, summary, now_str, payload_json,
            ),
        )

        # 3. Insert individual findings
        findings = record.get("bugs", []) + record.get("security_findings", [])
        for f in findings:
            fid = f"find-{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO findings (
                    id, session_id, file_path, line_number, severity,
                    category, rule_id, cwe_id, title, description, source, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fid,
                    session_id,
                    f.get("file", "main"),
                    int(f.get("line", 1)) if str(f.get("line", "1")).isdigit() else 1,
                    f.get("severity", "info"),
                    "security" if "cwe" in f or f.get("source") == "static-security" else "bug",
                    f.get("rule", ""),
                    f.get("cwe", ""),
                    f.get("title", f.get("rule", "Finding")),
                    f.get("description", ""),
                    f.get("source", "static"),
                    f.get("confidence", "high"),
                ),
            )

    return session_id


def get_recent_sessions(limit: int = 25, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Loads recent review sessions from database."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT payload_json FROM review_sessions
            ORDER BY rowid DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results = []
    for r in rows:
        try:
            results.append(json.loads(r["payload_json"]))
        except Exception:
            continue
    return results


def get_session_by_id(session_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves single review session by ID."""
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT payload_json FROM review_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if row:
        try:
            return json.loads(row["payload_json"])
        except Exception:
            return None
    return None


def get_dashboard_metrics(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Computes real, genuine metrics strictly from stored SQLite records.
    Never returns hardcoded placeholder numbers.
    """
    with get_db_connection(db_path) as conn:
        # Connected/reviewed repos
        repo_count = conn.execute(
            "SELECT COUNT(DISTINCT repo_full_name) as count FROM review_sessions"
        ).fetchone()["count"]

        # Total sessions
        session_count = conn.execute(
            "SELECT COUNT(*) as count FROM review_sessions"
        ).fetchone()["count"]

        # Total files reviewed
        files_sum = conn.execute(
            "SELECT COALESCE(SUM(files_analyzed), 0) as count FROM review_sessions"
        ).fetchone()["count"]

        # Average quality score
        avg_score_row = conn.execute(
            "SELECT AVG(overall_score) as avg_score FROM review_sessions"
        ).fetchone()
        avg_score = round(avg_score_row["avg_score"] or 0.0, 1)

        # Total bugs detected (findings where category='bug')
        total_bugs = conn.execute(
            "SELECT COUNT(*) as count FROM findings WHERE category = 'bug'"
        ).fetchone()["count"]

        # Critical security issues
        critical_sec = conn.execute(
            "SELECT COUNT(*) as count FROM findings WHERE category = 'security' AND severity = 'critical'"
        ).fetchone()["count"]

        # Findings by severity
        sev_rows = conn.execute(
            "SELECT severity, COUNT(*) as count FROM findings GROUP BY severity"
        ).fetchall()
        severity_dist = {r["severity"].lower(): r["count"] for r in sev_rows}

        # Quality trend over time (last 20 sessions)
        trend_rows = conn.execute(
            """
            SELECT id, repo_full_name, created_at, overall_score, critical_count, warning_count
            FROM review_sessions ORDER BY rowid ASC LIMIT 20
            """
        ).fetchall()
        quality_trends = [dict(r) for r in trend_rows]

        # Recent activities
        recent_rows = conn.execute(
            """
            SELECT id, repo_full_name, branch, commit_sha, overall_score, critical_count, warning_count, created_at
            FROM review_sessions ORDER BY rowid DESC LIMIT 10
            """
        ).fetchall()
        recent_activity = [dict(r) for r in recent_rows]

        # Issues per repository
        repo_issues_rows = conn.execute(
            """
            SELECT repo_full_name, COUNT(*) as issue_count
            FROM review_sessions s JOIN findings f ON s.id = f.session_id
            GROUP BY repo_full_name ORDER BY issue_count DESC LIMIT 10
            """
        ).fetchall()
        repo_issues = [dict(r) for r in repo_issues_rows]

    return {
        "connected_repositories": repo_count,
        "total_sessions": session_count,
        "total_files_reviewed": files_sum,
        "average_quality_score": avg_score,
        "total_bugs_detected": total_bugs,
        "critical_security_vulnerabilities": critical_sec,
        "severity_distribution": severity_dist,
        "quality_trends": quality_trends,
        "recent_activity": recent_activity,
        "repo_issues": repo_issues,
    }


def compare_two_sessions(
    base_session_id: str,
    target_session_id: str,
    db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """Compares two review sessions to find new issues, resolved issues, and score delta."""
    base = get_session_by_id(base_session_id, db_path)
    target = get_session_by_id(target_session_id, db_path)
    if not base or not target:
        return {"error": "One or both review sessions not found."}

    base_findings = base.get("bugs", []) + base.get("security_findings", [])
    target_findings = target.get("bugs", []) + target.get("security_findings", [])

    def _sig(f: Dict) -> str:
        return f"{f.get('file', '')}:{f.get('line', '')}:{f.get('rule', '')}:{f.get('title', '')}"

    base_map = {_sig(f): f for f in base_findings}
    target_map = {_sig(f): f for f in target_findings}

    new_issues = [f for sig, f in target_map.items() if sig not in base_map]
    resolved_issues = [f for sig, f in base_map.items() if sig not in target_map]

    base_score = base.get("overall_score", 0.0)
    target_score = target.get("overall_score", 0.0)
    score_delta = round(target_score - base_score, 1)

    return {
        "base_session_id": base_session_id,
        "target_session_id": target_session_id,
        "base_score": base_score,
        "target_score": target_score,
        "score_delta": score_delta,
        "new_issues": new_issues,
        "resolved_issues": resolved_issues,
        "new_count": len(new_issues),
        "resolved_count": len(resolved_issues),
    }


# Webhook event persistence & duplicate check
def is_duplicate_webhook(delivery_id: str, db_path: Path = DB_PATH) -> bool:
    """Checks if a delivery ID was already processed."""
    if not delivery_id:
        return False
    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT delivery_id FROM webhook_events WHERE delivery_id = ?",
            (delivery_id,),
        ).fetchone()
        return bool(row)


def save_webhook_event(
    delivery_id: str,
    repo_full_name: str,
    branch: str,
    commit_sha: str,
    status: str,
    message: str = "",
    db_path: Path = DB_PATH,
) -> None:
    """Records a webhook delivery event."""
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO webhook_events (delivery_id, repo_full_name, branch, commit_sha, status, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (delivery_id, repo_full_name, branch, commit_sha, status, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def get_recent_webhooks(limit: int = 15, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Lists recent webhook delivery events."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT delivery_id, repo_full_name, branch, commit_sha, status, message, created_at
            FROM webhook_events ORDER BY rowid DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# Persistent Assistant Chat Messages
def save_chat_message(
    repo_full_name: str,
    role: str,
    content: str,
    session_id: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Saves a conversation message with the AI Developer Assistant."""
    with get_db_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO assistant_messages (session_id, repo_full_name, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id or "", repo_full_name, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def get_chat_history(repo_full_name: str, limit: int = 30, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Loads chat history for a specific repository."""
    with get_db_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT role, content, created_at FROM assistant_messages
            WHERE repo_full_name = ? ORDER BY id ASC LIMIT ?
            """,
            (repo_full_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]
