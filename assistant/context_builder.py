"""
TechSpecAnalyser — Assistant Context Builder.
Constructs targeted, grounded codebase context from repository intelligence,
active findings, and relevant source snippets.
"""
import re
from typing import Any, Dict, List, Optional


class ContextBuilder:
    """Builds relevant context snippets for the AI Developer Assistant."""

    def __init__(self, max_context_chars: int = 15000):
        self.max_context_chars = max_context_chars

    def build_context(
        self,
        query: str,
        repo_data: Optional[Dict[str, Any]] = None,
        selected_finding: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Constructs grounded context for the user query."""
        sections = []

        if not repo_data:
            return "No active repository review loaded. Analysis facts are unavailable."

        # 1. Project High-Level Facts
        name = repo_data.get("repo_full_name") or repo_data.get("project_name", "Project")
        score = repo_data.get("overall_score", "N/A")
        files_count = repo_data.get("files_analyzed", 0)
        crit = repo_data.get("critical_count", 0)
        warn = repo_data.get("warning_count", 0)

        intel = repo_data.get("repository_intelligence") or {}
        arch = intel.get("architecture") or {}
        fw = ", ".join(intel.get("detected_frameworks", [])) or "standard libraries"

        sections.append(
            f"REPOSITORY: {name}\n"
            f"- Overall Code Quality Score: {score}/10\n"
            f"- Files Analyzed: {files_count}\n"
            f"- Total Critical Findings: {crit}, Warnings: {warn}\n"
            f"- Architecture Pattern: {arch.get('pattern', 'Modular')}\n"
            f"- Detected Frameworks: {fw}\n"
        )

        # 2. If a specific finding was selected by the user
        if selected_finding:
            sections.append(
                f"SELECTED FINDING:\n"
                f"- Title: {selected_finding.get('title', '')}\n"
                f"- File: {selected_finding.get('file', '')} (Line {selected_finding.get('line', 'N/A')})\n"
                f"- Severity: {selected_finding.get('severity', '')}\n"
                f"- Rule / CWE: {selected_finding.get('rule', '')} {selected_finding.get('cwe', '')}\n"
                f"- Description: {selected_finding.get('description', '')}\n"
                f"- Snippet: `{selected_finding.get('snippet', '')}`\n"
            )

        # 3. Relevant Findings based on query keywords
        q_lower = query.lower()
        findings = repo_data.get("bugs", []) + repo_data.get("security_findings", [])
        if "security" in q_lower or "cwe" in q_lower or "vulnerab" in q_lower:
            sec_findings = [f for f in findings if "cwe" in f or f.get("source") == "static-security"]
            sections.append("SECURITY VULNERABILITIES DETECTED:")
            for f in sec_findings[:10]:
                sections.append(f"- [{f.get('severity', '').upper()}] {f.get('file')}:{f.get('line')} - {f.get('title')}: {f.get('description')}")
        elif "bug" in q_lower or "error" in q_lower or "fix" in q_lower:
            bug_findings = [f for f in findings if f.get("source") != "static-security"]
            sections.append("KEY BUGS & CODE SMELLS DETECTED:")
            for f in bug_findings[:10]:
                sections.append(f"- [{f.get('severity', '').upper()}] {f.get('file')}:{f.get('line')} - {f.get('description')}")

        # 4. Endpoints & Models if requested
        if "api" in q_lower or "endpoint" in q_lower:
            endpoints = intel.get("detected_endpoints", [])
            sections.append("DETECTED API ENDPOINTS:")
            for ep in endpoints[:15]:
                sections.append(f"- {ep.get('method')} {ep.get('path')} in {ep.get('file')}")

        if "database" in q_lower or "model" in q_lower or "schema" in q_lower:
            models = intel.get("detected_models", [])
            sections.append("DETECTED DATABASE MODELS:")
            for m in models[:10]:
                sections.append(f"- Model `{m.get('name')}` in {m.get('file')}")

        # 5. File source snippets matching file names in query
        file_results = repo_data.get("file_results", [])
        for fr in file_results:
            fname = fr.get("file", "")
            if fname and (fname.lower() in q_lower or Path(fname).name.lower() in q_lower):
                code = fr.get("reviewed_code", "")
                if code:
                    sections.append(f"\nSOURCE OF {fname}:\n```\n{code[:3000]}\n```")

        context_text = "\n\n".join(sections)
        return context_text[: self.max_context_chars]
