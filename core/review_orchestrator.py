"""
TechSpecAnalyser — Review Orchestrator.
Coordinates single-file and multi-file code reviews across:
  1. Syntax validation gate
  2. Multi-language deterministic static & security analysis
  3. Complexity & Maintainability metrics
  4. Google Gemini GenAI review (when enabled)
  5. AI Improved-code syntax validator
  6. Transparent 4-pillar scoring engine
  7. Repository intelligence and SQLite persistence
"""
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from analyzers.complexity import analyze_complexity
from analyzers.static_analysis import analyze_static
from analyzers.syntax_checker import check_syntax
from config import detect_language
from core.gemini_client import GeminiClient
from core.repository_intelligence import RepositoryIntelligenceEngine
from core.scoring import compute_multi_factor_score
from database.repositories import save_review_session


class ReviewOrchestrator:
    """Central pipeline coordinator for single-code and repository reviews."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini = gemini_client or GeminiClient()
        self.repo_intel = RepositoryIntelligenceEngine()

    def review_single_code(
        self,
        code: str,
        language: str,
        file_path: str = "main.py",
        use_ai: bool = True,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Runs the 6-stage review pipeline for a single code snippet or file."""
        note = progress_cb or (lambda msg: None)
        start_time = time.time()
        now_str = datetime.now().strftime("%d %b %Y, %H:%M")

        result = {
            "id": f"rev-{uuid.uuid4().hex[:10]}",
            "time": now_str,
            "language": language,
            "file": file_path,
            "input_mode": "paste" if file_path == "main.py" else "single_file",
            "summary": "",
            "bugs": [],
            "security_findings": [],
            "improvements": [],
            "complexity_notes": "",
            "improved_code": "",
            "improved_code_valid": None,
            "improved_code_issues": [],
            "complexity": {},
            "scores": {},
            "overall_score": 0.0,
            "ai_status": "skipped" if not use_ai else "pending",
            "ai_error": None,
            "reviewed_code": code,
            "critical_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "duration_ms": 0,
            "error": False,
        }

        if not code or not code.strip():
            result.update({
                "summary": "No code was provided for review.",
                "complexity_notes": "N/A",
                "error": True,
            })
            return result

        # 1. Syntax Gate
        note("Checking syntax...")
        syntax = check_syntax(code, language, file_path)
        result["checker"] = syntax.get("checker", "")
        if not syntax["valid"]:
            result["bugs"] = syntax["bugs"]
            result["critical_count"] = len(syntax["bugs"])
            result["summary"] = "Syntax error detected. Address syntax errors first before proceeding."
            result["complexity_notes"] = "Complexity is evaluated after code syntax compiles successfully."
            result["overall_score"] = 1.0
            result["scores"] = {
                "overall_score": 1.0,
                "security_score": 10.0,
                "correctness_score": 1.0,
                "maintainability_score": 0.0,
                "complexity_score": 0.0,
                "penalties": ["Critical syntax failure prevents parsing."],
            }
            result["duration_ms"] = int((time.time() - start_time) * 1000)
            save_review_session(result)
            return result

        # 2. Static Analysis & Security Engine
        note("Running multi-language static & security analysis...")
        findings = analyze_static(code, language, file_path)
        bugs = [f for f in findings if f.get("source") != "static-security"]
        security_findings = [f for f in findings if f.get("source") == "static-security"]

        result["bugs"] = bugs
        result["security_findings"] = security_findings

        # 3. Complexity & Maintainability
        note("Computing cyclomatic complexity & software metrics...")
        complexity_data = analyze_complexity(code, language, file_path)
        result["complexity"] = complexity_data

        # 4. Google Gemini AI Review (if requested and enabled)
        ai_score = None
        if not use_ai:
            result["summary"] = "AI review disabled. Showing deterministic static analysis and software metrics."
            result["ai_status"] = "disabled"
        elif not self.gemini.is_configured:
            result["summary"] = "Operating in offline mode (GEMINI_API_KEY unconfigured). Showing deterministic static findings."
            result["ai_status"] = "offline"
        else:
            note("Invoking Google Gemini AI review...")
            ai_res = self.gemini.review_code(code, language, findings, file_path)
            if ai_res.get("status") == "ok":
                data = ai_res["data"]
                ai_score = data.get("overall_score")
                result["ai_status"] = "ok"
                result["summary"] = data.get("summary", "")
                result["improvements"] = data.get("improvements", [])
                result["complexity_notes"] = data.get("complexity_notes", "")
                result["improved_code"] = data.get("improved_code", "")

                # 5. AI Improved-Code Validation Gate
                if result["improved_code"]:
                    val = check_syntax(result["improved_code"], language)
                    result["improved_code_valid"] = val["valid"]
                    if not val["valid"]:
                        result["improved_code_issues"] = [b.get("description", "") for b in val["bugs"]]

                # Merge AI bugs safely
                for ab in data.get("bugs", []):
                    bugs.append({
                        "line": ab.get("line", "N/A"),
                        "severity": ab.get("severity", "warning"),
                        "title": "AI Logic Finding",
                        "description": ab.get("description", ""),
                        "fix": ab.get("fix", ""),
                        "file": file_path,
                        "source": "gemini-ai",
                        "confidence": "medium",
                    })
                result["bugs"] = bugs
            else:
                result["ai_status"] = ai_res.get("status", "failed")
                result["ai_error"] = ai_res.get("error")
                result["summary"] = f"AI review unavailable ({ai_res.get('error', '')}). Displaying local analysis."

        # 6. Multi-Factor Scoring
        note("Computing multi-factor score...")
        scores = compute_multi_factor_score(
            findings=result["bugs"] + result["security_findings"],
            complexity_data=complexity_data,
            ai_score=ai_score,
        )
        result["scores"] = scores
        result["overall_score"] = scores["overall_score"]

        # Counts
        all_issues = result["bugs"] + result["security_findings"]
        result["critical_count"] = len([f for f in all_issues if (f.get("severity") or "").lower() == "critical"])
        result["warning_count"] = len([f for f in all_issues if (f.get("severity") or "").lower() in ("warning", "high")])
        result["info_count"] = len([f for f in all_issues if (f.get("severity") or "").lower() in ("info", "low")])
        result["duration_ms"] = int((time.time() - start_time) * 1000)

        # Save to database
        save_review_session(result)
        return result

    def review_repository_files(
        self,
        files: List[Dict[str, Any]],
        project_name: str = "Repository Workspace",
        repo_url: str = "",
        branch: str = "main",
        commit_sha: str = "",
        use_ai: bool = True,
        progress_cb: Optional[Callable[[str, float], None]] = None,
    ) -> Dict[str, Any]:
        """
        Coordinates full repository review: per-file fault-isolated analysis,
        grounded repository intelligence, aggregate metrics, and DB persistence.
        """
        cb = progress_cb or (lambda msg, pct: None)
        start_time = time.time()
        now_str = datetime.now().strftime("%d %b %Y, %H:%M")

        cb("Analyzing repository structure & architecture...", 0.05)
        intel_report = self.repo_intel.analyze_repository(files, project_name)

        all_bugs: List[Dict[str, Any]] = []
        all_security: List[Dict[str, Any]] = []
        file_results: List[Dict[str, Any]] = []
        total_files = len(files)

        for idx, file_item in enumerate(files, 1):
            path = file_item.get("path", f"file_{idx}")
            content = file_item.get("content", "")
            lang = file_item.get("language") or detect_language(path)

            pct = 0.10 + 0.70 * (idx / max(total_files, 1))
            cb(f"Reviewing [{idx}/{total_files}]: {path} ({lang})...", pct)

            try:
                # Review file independently
                res = self.review_single_code(
                    code=content,
                    language=lang,
                    file_path=path,
                    use_ai=use_ai,
                )
                file_results.append(res)
                all_bugs.extend(res.get("bugs", []))
                all_security.extend(res.get("security_findings", []))
            except Exception as e:
                # Per-file failure isolation
                file_results.append({
                    "file": path,
                    "error": True,
                    "summary": f"File analysis failed: {e}",
                    "bugs": [],
                    "security_findings": [],
                    "overall_score": 5.0,
                })

        cb("Synthesizing repository quality scores...", 0.90)

        # Compute aggregate scores
        all_findings = all_bugs + all_security
        crit_count = len([f for f in all_findings if (f.get("severity") or "").lower() == "critical"])
        warn_count = len([f for f in all_findings if (f.get("severity") or "").lower() in ("warning", "high")])
        info_count = len([f for f in all_findings if (f.get("severity") or "").lower() in ("info", "low")])

        valid_file_scores = [r["overall_score"] for r in file_results if "overall_score" in r]
        avg_score = round(sum(valid_file_scores) / len(valid_file_scores), 1) if valid_file_scores else 7.0

        repo_record = {
            "id": f"repo-{uuid.uuid4().hex[:10]}",
            "project_id": project_name,
            "project_name": project_name,
            "repo_full_name": project_name,
            "repo_url": repo_url,
            "branch": branch,
            "commit_sha": commit_sha,
            "input_mode": "repository",
            "time": now_str,
            "files_analyzed": total_files,
            "file_results": file_results,
            "bugs": all_bugs,
            "security_findings": all_security,
            "critical_count": crit_count,
            "warning_count": warn_count,
            "info_count": info_count,
            "critical": crit_count,
            "warning": warn_count,
            "info": info_count,
            "overall_score": avg_score,
            "score": avg_score,
            "scores": {
                "overall_score": avg_score,
                "security_score": round(max(0.0, 10.0 - crit_count * 1.5 - warn_count * 0.5), 1),
                "correctness_score": round(max(0.0, 10.0 - crit_count * 1.0 - warn_count * 0.4), 1),
                "maintainability_score": 8.0,
                "complexity_score": 8.0,
            },
            "repository_intelligence": intel_report,
            "summary": (
                f"Completed repository review of `{project_name}` across {total_files} file(s). "
                f"Identified {crit_count} critical issues, {warn_count} warnings, and {info_count} suggestions. "
                f"Average code quality score: {avg_score}/10."
            ),
            "duration_ms": int((time.time() - start_time) * 1000),
        }

        save_review_session(repo_record)
        cb("Repository analysis complete.", 1.0)
        return repo_record
