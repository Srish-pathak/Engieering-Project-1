"""
FastAPI REST API server for CodeLens AI (optional standalone Python server).
In the integrated full-stack environment, `server.ts` invokes `codelens_engine.py`
and serves the same `/api/*` endpoints on port 3000.
"""
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from codelens_engine import (
    analyze_project_payload,
    clear_review_runs,
    load_review_runs,
    run_experimental_evaluation,
    save_review_run,
    validate_and_extract_zip,
)

app = FastAPI(
    title="CodeLens AI API",
    description="Static-Analysis-Grounded Multi-Agent System for Automated Code Review and Documentation Generation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    project_name: Optional[str] = "CodeLens Workspace"
    input_mode: Optional[str] = "paste"
    code: Optional[str] = ""
    language: Optional[str] = "Python"
    file_name: Optional[str] = "main.py"
    files: Optional[List[Dict[str, Any]]] = None
    use_ai: Optional[bool] = True


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "CodeLens AI FastAPI Engine"}


@app.post("/api/analyze")
def analyze_endpoint(req: AnalyzeRequest):
    return analyze_project_payload(req.model_dump())


@app.get("/api/history")
def get_history():
    return {"history": load_review_runs()}


@app.delete("/api/history")
def delete_history():
    return {"history": clear_review_runs()}


@app.get("/api/evaluate")
def evaluate_approaches():
    return run_experimental_evaluation()
