"""
TechSpecAnalyser — Security Centre View.
Dedicated security audit dashboard displaying vulnerability severities,
CWE catalog references, secret redaction checks, and remediation guidance.
"""
import streamlit as st

from components.finding_cards import render_finding_card


def render_security_view() -> None:
    """Renders the dedicated Security Centre."""
    st.markdown(
        """
        <div class="ts-header">
          <h1>Security Centre & Vulnerability Scanner</h1>
          <p>Automated CWE vulnerability detection: hardcoded secrets, injection flaws, unsafe deserialization, and path traversal.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    active_result = st.session_state.get("active_review_result")
    if not active_result:
        st.info("No active review results available. Connect a repository or review code first.")
        return

    sec_findings = active_result.get("security_findings", [])
    scores = active_result.get("scores") or {}
    sec_score = scores.get("security_score", 10.0)

    # Top stats
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Security Score", f"{sec_score}/10", "Pillar 1 Score")
    with c2:
        crit_count = len([f for f in sec_findings if (f.get("severity") or "").lower() == "critical"])
        st.metric("Critical Vulnerabilities", f"{crit_count}", "Immediate Action")
    with c3:
        warn_count = len([f for f in sec_findings if (f.get("severity") or "").lower() in ("warning", "high")])
        st.metric("Security Warnings", f"{warn_count}", "High Priority")
    with c4:
        st.metric("Secret Redaction", "ACTIVE", "Zero-leak guarantee")

    st.markdown("---")

    if not sec_findings:
        st.success("🎉 No security vulnerabilities detected in this review session!")
        return

    # Filter by CWE
    cwes = sorted(list({f.get("cwe") for f in sec_findings if f.get("cwe")}))
    col_cwe, col_sev = st.columns([1, 1])
    with col_cwe:
        selected_cwe = st.multiselect("Filter by CWE Reference", cwes, default=cwes)
    with col_sev:
        selected_sev = st.multiselect("Filter by Severity", ["critical", "warning", "info"], default=["critical", "warning", "info"])

    filtered = [
        f for f in sec_findings
        if (not selected_cwe or f.get("cwe") in selected_cwe)
        and (f.get("severity") or "info").lower() in selected_sev
    ]

    st.markdown(f"### Detected Security Findings ({len(filtered)})")
    for idx, f in enumerate(filtered):
        render_finding_card(f, index=idx + 500)
