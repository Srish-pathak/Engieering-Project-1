"""
TechSpecAnalyser — AI Developer Assistant Engine.
Provides grounded repository-level conversation, finding explanations,
and patch suggestions with persistent history.
"""
from typing import Any, Dict, List, Optional

from assistant.context_builder import ContextBuilder
from core.gemini_client import GeminiClient
from database.repositories import get_chat_history, save_chat_message


class CodebaseAssistant:
    """Assistant answering developer questions grounded in active repository data."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini = gemini_client or GeminiClient()
        self.context_builder = ContextBuilder()

    def ask(
        self,
        query: str,
        repo_data: Optional[Dict[str, Any]] = None,
        selected_finding: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Processes a developer query against the active repository."""
        repo_name = (repo_data.get("repo_full_name") or repo_data.get("project_name", "general")) if repo_data else "general"

        # 1. Build grounded context
        context = self.context_builder.build_context(query, repo_data, selected_finding)

        # 2. Get past history
        history = get_chat_history(repo_name, limit=6)

        # 3. Call Gemini
        answer = self.gemini.chat_with_repo(query, context, history)

        # 4. Save to persistent DB
        save_chat_message(repo_name, "user", query)
        save_chat_message(repo_name, "assistant", answer)

        return answer

    def explain_finding(
        self,
        finding: Dict[str, Any],
        code: str,
        language: str,
    ) -> str:
        """Explains a specific security or bug finding and its consequences."""
        query = (
            f"Explain this finding in detail:\n"
            f"Title: {finding.get('title')}\n"
            f"Description: {finding.get('description')}\n"
            f"File: {finding.get('file')} Line: {finding.get('line')}\n"
            f"Rule: {finding.get('rule')} CWE: {finding.get('cwe', 'N/A')}\n"
            "Explain why this is an issue, how an attacker or runtime error could exploit it, and best practice."
        )
        return self.ask(query, repo_data={"repo_full_name": "Finding Explanation", "bugs": [finding]}, selected_finding=finding)

    def generate_fix(
        self,
        finding: Dict[str, Any],
        code: str,
        language: str,
    ) -> Dict[str, Any]:
        """Generates an AI fix for a selected finding."""
        return self.gemini.generate_fix_for_finding(finding, code, language)
