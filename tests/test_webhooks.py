"""
TechSpecAnalyser — Webhook Verification & FastAPI Endpoint Test Suite.
Tests HMAC-SHA256 signature checking, push event parsing, and duplicate protection.
"""
import hashlib
import hmac
import json
from fastapi.testclient import TestClient

from api import app
from config import WEBHOOK_SECRET
from integrations.github_webhooks import parse_push_payload, verify_webhook_signature


def _make_signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    h = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={h}"


def test_hmac_signature_verification():
    body = b'{"ref": "refs/heads/main"}'
    valid_sig = _make_signature(body, WEBHOOK_SECRET)
    invalid_sig = "sha256=badbadbadbadbadbadbadbadbadbadbadbadbadbadbadbad"

    assert verify_webhook_signature(body, valid_sig, WEBHOOK_SECRET) is True
    assert verify_webhook_signature(body, invalid_sig, WEBHOOK_SECRET) is False
    assert verify_webhook_signature(body, None, WEBHOOK_SECRET) is False
    assert verify_webhook_signature(body, "invalid_prefix", WEBHOOK_SECRET) is False


def test_parse_push_payload():
    payload = {
        "ref": "refs/heads/feature-auth",
        "repository": {
            "name": "my-app",
            "full_name": "developer/my-app",
            "owner": {"name": "developer"},
        },
        "head_commit": {
            "id": "abc1234567890",
            "message": "Add user authentication module",
            "author": {"username": "srishti"},
            "added": ["auth.py"],
            "modified": ["app.py"],
        },
        "commits": [],
    }

    info = parse_push_payload(payload)
    assert info["branch"] == "feature-auth"
    assert info["repo_full_name"] == "developer/my-app"
    assert info["commit_sha"] == "abc1234"
    assert info["author"] == "srishti"
    assert "auth.py" in info["changed_files"]
    assert "app.py" in info["changed_files"]


def test_webhook_endpoint_rejects_invalid_signature():
    client = TestClient(app)
    resp = client.post(
        "/webhooks/github",
        content=b'{"test": 1}',
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )
    assert resp.status_code == 401


def test_webhook_endpoint_handles_ping_event():
    client = TestClient(app)
    body = json.dumps({"zen": "Keep it logically awesome."}).encode("utf-8")
    sig = _make_signature(body)

    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "ping",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert "Pong" in resp.json().get("message", "")


def test_webhook_endpoint_accepts_push_and_enqueues():
    client = TestClient(app)
    payload = {
        "ref": "refs/heads/main",
        "repository": {"name": "test-repo", "full_name": "org/test-repo"},
        "head_commit": {"id": "123456789", "message": "Fix typo", "added": [], "modified": ["main.py"]},
    }
    body = json.dumps(payload).encode("utf-8")
    sig = _make_signature(body)

    import uuid
    deliv_id = f"delivery-{uuid.uuid4().hex}"

    resp = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": deliv_id,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    # Verify duplicate event protection
    resp_dup = client.post(
        "/webhooks/github",
        content=body,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": deliv_id,
            "Content-Type": "application/json",
        },
    )
    assert resp_dup.status_code == 200
    assert resp_dup.json()["status"] == "skipped"
