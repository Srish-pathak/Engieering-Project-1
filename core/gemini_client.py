"""
TechSpecAnalyser — Google Gemini AI Engine.
Integrates the official Google Gen AI SDK (google-genai) with
automatic secret redaction, rate limit backoff, quota circuit breaker,
and offline fallback resilience.
"""
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from config import (
    AI_MAX_ATTEMPTS,
    AI_RETRY_DELAY,
    DEFAULT_GEMINI_MODEL,
    MAX_CODE_CHARS,
    get_gemini_api_key,
)
from core.security_redactor import redact_secrets

RETRYABLE_CODES = {429, 500, 502, 503, 504}


class BugItem(BaseModel):
    line: str
    severity: str
    description: str
    fix: str


class ImprovementItem(BaseModel):
    title: str
    detail: str


class ReviewResponseSchema(BaseModel):
    summary: str
    bugs: List[BugItem]
    improvements: List[ImprovementItem]
    complexity_notes: str
    improved_code: str
    overall_score: int


class GeminiClient:
    """Manages Google Gemini GenAI interactions with fault tolerance."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = get_gemini_api_key(api_key)
        self.model_name = (model_name or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip()
        self._quota_exhausted = False
        self._last_error = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key) and not self._quota_exhausted

    @property
    def quota_exhausted(self) -> bool:
        return self._quota_exhausted

    def get_client(self) -> genai.Client:
        if not self.api_key:
            raise EnvironmentError("GEMINI_API_KEY is not configured.")
        return genai.Client(api_key=self.api_key)

    def review_code(
        self,
        code: str,
        language: str,
        known_findings: Optional[List[Dict[str, Any]]] = None,
        file_path: str = "",
    ) -> Dict[str, Any]:
        """
        Sends code and known deterministic findings to Gemini for expert review,
        architectural observations, and complete improved code.
        """
        if self._quota_exhausted:
            return {"status": "quota_exhausted", "error": "AI review skipped: API quota reached."}

        if not self.api_key:
            return {"status": "unconfigured", "error": "GEMINI_API_KEY not configured."}

        # Redact secrets before sending to Google Gemini!
        sanitized_code, _ = redact_secrets(code)

        if len(sanitized_code) > MAX_CODE_CHARS:
            return {
                "status": "skipped",
                "error": f"Code length ({len(sanitized_code)} chars) exceeds maximum limit ({MAX_CODE_CHARS}).",
            }

        known_str = "\n".join(
            f"- Line {f.get('line', '?')} [{f.get('severity', 'info')}]: {f.get('description', '')}"
            for f in (known_findings or [])
        ) or "(none)"

        prompt = (
            f"Review this {language} source file: `{file_path or 'code'}`.\n\n"
            f"<known_deterministic_findings>\n{known_str}\n</known_deterministic_findings>\n\n"
            f"<code_to_review>\n{sanitized_code}\n</code_to_review>"
        )

        system_instruction = (
            "You are TechSpecAnalyser's Senior Review Agent. Analyze the provided source code data. "
            "Never invent hallucinated bugs. Focus on real logic bugs, runtime errors, and architectural patterns. "
            "Return a complete improved_code implementation in the same language without line numbers or markdown fences. "
            "Score from 1 to 10 based on production quality."
        )

        try:
            client = self.get_client()
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=ReviewResponseSchema,
            )

            response = self._execute_with_retry(client, prompt, config)
            data = json.loads(response.text)
            return {"status": "ok", "data": data, "model": self.model_name}

        except genai_errors.APIError as e:
            code_num = getattr(e, "code", None)
            if code_num == 429:
                self._quota_exhausted = True
                self._last_error = "Gemini API rate limit or quota exceeded."
            else:
                self._last_error = f"Gemini API Error ({code_num}): {e}"
            return {"status": "failed", "error": self._last_error}
        except Exception as e:
            self._last_error = f"AI review failed: {e}"
            return {"status": "failed", "error": self._last_error}

    def generate_fix_for_finding(
        self,
        finding: Dict[str, Any],
        code: str,
        language: str,
    ) -> Dict[str, Any]:
        """Generates an AI patch for a specific finding."""
        if not self.is_configured:
            return {"status": "failed", "error": "Gemini AI not configured or quota reached."}

        sanitized_code, _ = redact_secrets(code)

        prompt = (
            f"Fix this {language} issue in the code:\n"
            f"Issue: {finding.get('title', 'Bug')} - {finding.get('description', '')}\n"
            f"Line: {finding.get('line', 'N/A')}\n"
            f"Rule: {finding.get('rule', '')} {finding.get('cwe', '')}\n\n"
            f"Code:\n```\n{sanitized_code}\n```\n\n"
            "Provide the complete corrected code and a 1-2 sentence explanation of what was changed."
        )

        try:
            client = self.get_client()
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            raw = response.text or ""
            # Extract code block if wrapped
            code_match = re.search(r"```[\w+]*\n(.*?)```", raw, re.DOTALL)
            fixed_code = code_match.group(1) if code_match else raw
            return {
                "status": "ok",
                "fixed_code": fixed_code.strip(),
                "explanation": "Fix generated by TechSpecAnalyser AI Agent.",
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def chat_with_repo(
        self,
        query: str,
        repo_context: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Grounds repository assistant answers in real codebase evidence."""
        if not self.is_configured:
            return (
                "AI Assistant is currently operating in offline mode. "
                "Configure a valid GEMINI_API_KEY in the sidebar or .env file to enable codebase AI chat."
            )

        sanitized_context, _ = redact_secrets(repo_context)

        system_instruction = (
            "You are TechSpecAnalyser Developer Assistant. You have access to real analysis results "
            "and file contents from the user's repository. "
            "Answer questions strictly grounded in the provided repository facts. "
            "Always cite relevant file names and line numbers where available. "
            "If a file or detail is not present in the provided context, state clearly that it was not retrieved."
        )

        full_prompt = (
            f"<repository_facts_and_context>\n{sanitized_context}\n</repository_facts_and_context>\n\n"
            f"User Question: {query}"
        )

        try:
            client = self.get_client()
            response = client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.3),
            )
            return response.text or "No response generated."
        except Exception as e:
            return f"Assistant request failed: {e}"

    def _execute_with_retry(self, client: genai.Client, prompt: str, config: Any) -> Any:
        """Executes Gemini generate_content with exponential backoff on transient errors."""
        for attempt in range(AI_MAX_ATTEMPTS):
            try:
                return client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
            except genai_errors.APIError as e:
                code_num = getattr(e, "code", None)
                if code_num in RETRYABLE_CODES and attempt < AI_MAX_ATTEMPTS - 1:
                    time.sleep(AI_RETRY_DELAY * (2 ** attempt))
                    continue
                raise
