"""
TechSpecAnalyser — Repository Intelligence View.
Presents grounded technical architecture, detected API endpoints, database models,
environment variables, and generated comprehensive Markdown documentation.
"""
import streamlit as st

from reports.export import file_stem


def render_intelligence_view() -> None:
    """Renders the Understand My Project intelligence dashboard."""
    st.markdown(
        """
        <div class="ts-header">
          <h1>Repository Intelligence & Architecture</h1>
          <p>Deep deterministic codebase understanding: stack deduction, API endpoints, schemas, and auto-generated technical documentation.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    active_result = st.session_state.get("active_review_result")
    if not active_result or "repository_intelligence" not in active_result:
        st.info("No active repository intelligence report loaded. Connect and analyze a repository in **Add Repository** first.")
        if st.button("🔗 Go to Add Repository"):
            st.session_state["active_nav"] = "🔗 Add Repository"
            st.rerun()
        return

    intel = active_result["repository_intelligence"]
    overview = intel.get("overview", {})
    arch = intel.get("architecture", {})
    doc_markdown = intel.get("documentation", "")
    p_name = intel.get("project_name", "Repository")

    # Top summary cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Primary Language", intel.get("primary_language", "Python"), f"{intel.get('total_files', 0)} files")
    with c2:
        st.metric("Total Lines of Code", f"{intel.get('total_loc', 0):,}", "Excluding comments/blanks")
    with c3:
        st.metric("Detected Endpoints", f"{len(intel.get('detected_endpoints', []))}", "HTTP routes")
    with c4:
        st.metric("Database Models", f"{len(intel.get('detected_models', []))}", "Detected schemas")

    st.write("")

    # Sub-tabs
    tab_overview, tab_arch, tab_endpoints, tab_env, tab_docs = st.tabs([
        "📋 Project Overview",
        "🏛️ Technical Architecture",
        "🌐 Endpoints & Models",
        "🔑 Env Variables & Config",
        "📄 Generated Documentation",
    ])

    with tab_overview:
        st.markdown(f"### About `{p_name}`")
        st.write(overview.get("summary", ""))

        st.markdown("#### Primary Purpose & Scope")
        st.write(overview.get("primary_purpose", ""))

        st.markdown("#### Target Audience & User Personas")
        st.write(overview.get("target_audience", ""))

        st.markdown("#### Detected Technologies & Frameworks")
        fw_list = intel.get("detected_frameworks", [])
        if fw_list:
            for fw in fw_list:
                st.markdown(f"- 📦 **{fw}**")
        else:
            st.caption("Standard language primitives detected.")

    with tab_arch:
        st.markdown("### Technical Architecture & Data Flow")
        st.markdown(f"- **Architectural Pattern:** {arch.get('pattern')}")
        st.markdown(f"- **Frontend Tier:** {arch.get('frontend')}")
        st.markdown(f"- **Backend Tier:** {arch.get('backend')}")
        st.markdown(f"- **Data Storage Layer:** {arch.get('storage')}")

        st.markdown("#### Entry Points")
        entry_points = intel.get("entry_points", [])
        if entry_points:
            for ep in entry_points:
                st.markdown(f"- 🚀 `{ep}`")
        else:
            st.caption("No standard entry point file (app.py, main.py, server.ts) detected.")

    with tab_endpoints:
        col_ep, col_mo = st.columns(2)
        with col_ep:
            st.markdown("### Detected API Endpoints")
            eps = intel.get("detected_endpoints", [])
            if eps:
                st.dataframe(eps, use_container_width=True)
            else:
                st.info("No REST API route decorators detected in analyzed files.")

        with col_mo:
            st.markdown("### Detected Database Models")
            models = intel.get("detected_models", [])
            if models:
                st.dataframe(models, use_container_width=True)
            else:
                st.info("No ORM schema classes detected.")

    with tab_env:
        st.markdown("### Environment Variables Referenced in Code")
        evs = intel.get("env_vars_referenced", [])
        if evs:
            st.markdown("These environment variables are directly read by application source files:")
            for ev in evs:
                st.markdown(f"- `os.getenv('{ev}')`")
        else:
            st.info("No environment variables directly accessed in analyzed files.")

    with tab_docs:
        st.markdown("### Comprehensive Technical Documentation (Markdown)")
        stem = file_stem(p_name)
        st.download_button(
            "📥 Download PROJECT_DOCUMENTATION.md",
            data=doc_markdown,
            file_name=f"{stem}_DOCUMENTATION.md",
            mime="text/markdown",
        )
        st.markdown(doc_markdown)
