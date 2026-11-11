"""
TechSpecAnalyser — GitHub Webhook Processing Engine.
Handles HMAC-SHA256 signature verification, push payload parsing,
duplicate event protection, and automated background analysis pipeline execution.
"""
import hashlib
import hmac
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("TechSpecAnalyser.Webhooks")


def verify_webhook_signature(
    payload_body: bytes,
    signature_header: Optional[str],
    secret: str,
) -> bool:
    """
    Verifies GitHub's HMAC-SHA256 signature (X-Hub-Signature-256).
    """
    if not signature_header or not secret:
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    expected_sig = signature_header[len(prefix):].strip()
    computed_sig = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_sig, computed_sig)


def parse_push_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts relevant repository and commit metadata from a GitHub 'push' event payload.
    """
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name", "")
    owner = repo.get("owner", {}).get("name") or repo.get("owner", {}).get("login") or ""
    repo_name = repo.get("name", "")

    ref = payload.get("ref", "")
    branch = ref.split("/")[-1] if ref.startswith("refs/heads/") else ref

    head_commit = payload.get("head_commit") or {}
    commit_sha = head_commit.get("id", "") or payload.get("after", "")
    commit_message = head_commit.get("message", "No commit message")
    author = head_commit.get("author", {}).get("username") or head_commit.get("author", {}).get("name") or "developer"

    # Collect all modified and added files across the commits
    changed_files = set()
    for commit in payload.get("commits", []):
        changed_files.update(commit.get("added", []))
        changed_files.update(commit.get("modified", []))

    if not changed_files and head_commit:
        changed_files.update(head_commit.get("added", []))
        changed_files.update(head_commit.get("modified", []))

    return {
        "event_type": "push",
        "repo_full_name": repo_full_name,
        "owner": owner,
        "repo": repo_name,
        "branch": branch,
        "commit_sha": commit_sha[:7],
        "full_commit_sha": commit_sha,
        "commit_message": commit_message.splitlines()[0] if commit_message else "",
        "author": author,
        "changed_files": sorted(changed_files),
        "sender": payload.get("sender", {}).get("login", ""),
    }
