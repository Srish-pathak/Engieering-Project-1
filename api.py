"""
TechSpecAnalyser — FastAPI REST API & GitHub Webhook Service.
Run with: uvicorn api:app --host 0.0.0.0 --port 8000
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    DB_PATH,
    WEBHOOK_SECRET,
    is_gemini_configured,
)
from core.gemini_client import GeminiClient
from core.review_orchestrator import ReviewOrchestrator
from database.repositories import (
    get_dashboard_metrics,
    get_recent_sessions,
    get_recent_webhooks,
    is_duplicate_webhook,
    save_webhook_event,
)
from integrations.github_client import GitHubClient
from integrations.github_fetcher import GitHubFetcher
from integrations.github_webhooks import parse_push_payload, verify_webhook_signature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TechSpecAnalyser.API")

app = FastAPI(
    title=f"{APP_NAME} API",
    description=APP_TAGLINE,
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ReviewOrchestrator()


class CodeReviewRequest(BaseModel):
    code: str
    language: str = "Python"
    file_path: Optional[str] = "main.py"
    use_ai: Optional[bool] = True


def _process_webhook_push_background(event_info: Dict[str, Any], delivery_id: str) -> None:
    """Background task executing the analysis pipeline for newly pushed commits."""
    owner = event_info.get("owner", "")
    repo = event_info.get("repo", "")
    repo_full_name = event_info.get("repo_full_name", f"{owner}/{repo}")
    branch = event_info.get("branch", "main")
    commit_sha = event_info.get("commit_sha", "")

    logger.info(f"Processing webhook push for {repo_full_name} ({branch} @ {commit_sha})")
    try:
        # Download files and run review
        fetcher = GitHubFetcher()
        files, _ = fetcher.fetch_repository_files(owner, repo, branch=branch)

        result = orchestrator.review_repository_files(
            files=files,
            project_name=repo_full_name,
            branch=branch,
            commit_sha=commit_sha,
            use_ai=is_gemini_configured(),
        )

        save_webhook_event(
            delivery_id=delivery_id,
            repo_full_name=repo_full_name,
            branch=branch,
            commit_sha=commit_sha,
            status="success",
            message=f"Reviewed {len(files)} files. Score: {result.get('overall_score')}/10",
        )
        logger.info(f"Webhook push analysis completed successfully for {repo_full_name}")

    except Exception as e:
        logger.error(f"Webhook background processing failed for {repo_full_name}: {e}")
        save_webhook_event(
            delivery_id=delivery_id,
            repo_full_name=repo_full_name,
            branch=branch,
            commit_sha=commit_sha,
            status="error",
            message=str(e),
        )


@app.get("/")
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
        "gemini_configured": is_gemini_configured(),
        "database": str(DB_PATH),
    }


@app.post("/webhooks/github")
async def github_webhook_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header("push"),
    x_github_delivery: Optional[str] = Header(None),
):
    """
    Receives and processes GitHub push webhooks.
    Validates HMAC-SHA256 signature, deduplicates delivery IDs,
    and enqueues background automated analysis.
    """
    body_bytes = await request.body()

    # 1. Signature Verification
    if not verify_webhook_signature(body_bytes, x_hub_signature_256, WEBHOOK_SECRET):
        logger.warning("Webhook HMAC signature verification failed.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC-SHA256 signature in X-Hub-Signature-256 header.",
        )

    # 2. Ping Event Handling (GitHub sends ping upon creating a webhook)
    if x_github_event == "ping":
        return {"status": "ok", "message": "Pong! Webhook successfully configured with TechSpecAnalyser."}

    # 3. Duplicate Delivery Protection
    delivery_id = x_github_delivery or ""
    if delivery_id and is_duplicate_webhook(delivery_id):
        logger.info(f"Duplicate webhook delivery `{delivery_id}` skipped.")
        return {"status": "skipped", "reason": "Duplicate delivery ID"}

    # 4. Parse Push Payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body in webhook request.")

    if x_github_event != "push":
        return {"status": "ignored", "event": x_github_event, "message": "Only 'push' events trigger automated reviews."}

    event_info = parse_push_payload(payload)

    # Record initial webhook receipt
    save_webhook_event(
        delivery_id=delivery_id or f"del-{event_info['commit_sha']}",
        repo_full_name=event_info["repo_full_name"],
        branch=event_info["branch"],
        commit_sha=event_info["commit_sha"],
        status="enqueued",
        message=f"Received push from {event_info['author']}: {event_info['commit_message']}",
    )

    # 5. Enqueue background review task
    background_tasks.add_task(
        _process_webhook_push_background,
        event_info,
        delivery_id or f"del-{event_info['commit_sha']}",
    )

    return {
        "status": "accepted",
        "repository": event_info["repo_full_name"],
        "branch": event_info["branch"],
        "commit": event_info["commit_sha"],
        "changed_files_count": len(event_info["changed_files"]),
        "message": "Automated push review pipeline enqueued.",
    }


@app.post("/api/analyze")
def analyze_code_endpoint(req: CodeReviewRequest):
    """Performs real-time code review on submitted snippet."""
    return orchestrator.review_single_code(
        code=req.code,
        language=req.language,
        file_path=req.file_path or "main.py",
        use_ai=req.use_ai if req.use_ai is not None else True,
    )


@app.get("/api/dashboard")
def dashboard_metrics_endpoint():
    """Returns genuine stored dashboard statistics."""
    return get_dashboard_metrics()


@app.get("/api/history")
def history_endpoint(limit: int = 25):
    """Lists recent review session payloads."""
    return {"sessions": get_recent_sessions(limit=limit)}


@app.get("/api/webhooks/recent")
def recent_webhooks_endpoint(limit: int = 15):
    """Lists recent webhook delivery logs."""
    return {"webhooks": get_recent_webhooks(limit=limit)}
