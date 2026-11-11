"""
TechSpecAnalyser — Finding Card UI Component.
Renders actionable findings with severity pills, CWE badges,
evidence snippets, explanations, and remediation steps.
"""
import html
from typing import Any, Callable, Dict, Optional

import streamlit as st


def render_finding_card(
    finding: Dict[str, Any],
    index: int = 0,
    on_fix_click: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_explain_click: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> None:
    """Renders a single actionable finding card inside Streamlit."""
    sev = (finding.get("severity") or "info").lower()
    title = html.escape(finding.get("title") or finding.get("rule", "Finding"))
    desc = html.escape(finding.get("description", ""))
    file_path = html.escape(str(finding.get("file", "code")))
    line = finding.get("line", "N/A")
    rule = html.escape(finding.get("rule", ""))
    cwe = html.escape(finding.get("cwe", ""))
    source = html.escape(finding.get("source", "static"))
    snippet = finding.get("snippet", "")
    why_problem = finding.get("why_problem", "")
    remediation = finding.get("remediation") or finding.get("fix", "")

    # Card class based on severity
    css_class = "ts-finding-crit" if sev == "critical" else "ts-finding-warn" if sev in ("warning", "high") else "ts-finding-info"
    badge_class = "ts-badge-crit" if sev == "critical" else "ts-badge-warn" if sev in ("warning", "high") else "ts-badge-info"

    # HTML header & body
    cwe_badge = f'<span class="ts-badge ts-badge-crit">{cwe}</span>' if cwe else ""
    source_badge = f'<span class="ts-badge ts-badge-source">{source}</span>'

    card_html = f"""
    <div class="ts-finding {css_class}">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
        <div>
          <span class="ts-badge {badge_class}">{sev.upper()}</span>
          {cwe_badge}
          {source_badge}
        </div>
        <div style="color:var(--muted); font-size:0.85rem; font-family:'JetBrains Mono', monospace;">
          {file_path}:{line}
        </div>
      </div>
      <div style="font-weight:700; font-size:1.05rem; margin-bottom:0.25rem;">{title}</div>
      <div style="color:var(--text); font-size:0.92rem; line-height:1.4;">{desc}</div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Expandable details section
    with st.expander(f"🔍 Inspect Evidence & Remediation ({file_path}:{line})", expanded=False):
        if snippet:
            st.markdown(f"**Evidence Code Snippet (Line {line}):**")
            st.code(snippet, language="python")

        if why_problem:
            st.markdown(f"**Why this is an issue:**\n{why_problem}")

        if remediation:
            st.markdown(f"**Suggested Remediation:**\n{remediation}")

        # Action buttons
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💬 Ask Assistant About Finding", key=f"explain_{index}_{file_path}_{line}"):
                if on_explain_click:
                    on_explain_click(finding)
                st.session_state["assistant_finding_context"] = finding
                st.session_state["active_nav"] = "💬 AI Developer Assistant"
                st.rerun()

        with col2:
            if st.button("✨ Request AI Patch & Diff", key=f"fix_{index}_{file_path}_{line}"):
                if on_fix_click:
                    on_fix_click(finding)
                st.session_state["fix_target_finding"] = finding
                st.session_state["active_nav"] = "🔍 Code Review"
                st.rerun()
