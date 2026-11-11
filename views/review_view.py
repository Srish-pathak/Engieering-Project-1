"""
TechSpecAnalyser — Code Review Workspace View.
Supports pasted source code, single file uploads, and full repository reviews
with actionable finding filters, diff viewers, and report exporters.
"""
from typing import Any, Dict, List

import streamlit as st

from components.charts import render_complexity_distribution, render_health_radar_chart
from components.code_diff import render_code_comparison
from components.finding_cards import render_finding_card
from config import EXTENSION_TO_LANGUAGE, is_gemini_configured
from core.review_orchestrator import ReviewOrchestrator
from reports.export import build_csv, build_json, build_markdown, file_stem
from samples import SAMPLES

try:
    from streamlit_ace import st_ace
    HAS_ACE = True
except ImportError:
    HAS_ACE = False

SUPPORTED_LANGUAGES = ["Python", "C", "C++", "Java", "JavaScript", "JSX", "TypeScript", "TSX", "HTML", "CSS", "SCSS"]


def render_review_view() -> None:
    """Renders the comprehensive Code Review Workspace."""
    st.markdown(
        """
        <div class="ts-header">
          <h1>Code Review Workspace</h1>
          <p>Multi-language deterministic static analysis grounded with Google Gemini AI review.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Top selector: Paste code vs View active repository results
    active_result = st.session_state.get("active_review_result")

    col_mode1, col_mode2 = st.columns([1, 1])
    with col_mode1:
        input_type = st.radio(
            "Review Mode",
            ["Paste Code / Single File", "Active Repository Review" if active_result else "No Active Repository"],
            horizontal=True,
            index=1 if (active_result and st.session_state.get("prefer_active_repo")) else 0,
        )

    if input_type == "Paste Code / Single File":
        _render_single_code_input()

    active_result = st.session_state.get("active_review_result")
    if not active_result:
        st.info("Paste or submit code above, or connect a repository in **Add Repository** to see review results.")
        return

    # Render review workspace tabs
    _render_results_tabs(active_result)


def _render_single_code_input() -> None:
    """Renders the single-code editor, sample picker, and submit button."""
    col_lang, col_sample, col_ai = st.columns([1, 1, 1])
    with col_lang:
        language = st.selectbox("Select Language", SUPPORTED_LANGUAGES, index=0)

    with col_sample:
        sample_keys = [k for k in SAMPLES.keys() if language in k or (language == "Python" and "Python" in k)]
        sample_options = ["(Custom Code)"] + list(SAMPLES.keys())
        chosen_sample = st.selectbox("Load Sample Case", sample_options)

    with col_ai:
        st.write("")
        st.write("")
        use_ai = st.checkbox("Enable Google Gemini AI", value=is_gemini_configured())

    # Preload sample code if selected
    default_code = SAMPLES.get(chosen_sample, {}).get("code", "") if chosen_sample != "(Custom Code)" else ""
    if not default_code and "editor_code" in st.session_state:
        default_code = st.session_state["editor_code"]

    st.markdown("**Source Code Editor:**")
    if HAS_ACE:
        code_input = st_ace(
            value=default_code,
            language=language.lower() if language != "C++" else "c_cpp",
            theme="monokai",
            height=280,
            key="ace_editor",
        )
    else:
        code_input = st.text_area("Source Code", value=default_code, height=280, key="text_editor")

    st.session_state["editor_code"] = code_input

    if st.button("🚀 Run Comprehensive Code Review", type="primary"):
        if not code_input.strip():
            st.warning("Please provide source code to review.")
            return

        orchestrator = ReviewOrchestrator()
        with st.spinner("Analyzing code with deterministic AST rules & Gemini..."):
            res = orchestrator.review_single_code(
                code=code_input,
                language=language,
                use_ai=use_ai,
            )
            st.session_state["active_review_result"] = res
            st.session_state["prefer_active_repo"] = False
            st.rerun()


def _render_results_tabs(result: Dict[str, Any]) -> None:
    """Renders the detailed tabs and actionable cards."""
    st.markdown("---")

    # Score Banner
    score = result.get("overall_score", 0.0)
    scores = result.get("scores") or {}
    name = result.get("repo_full_name") or result.get("project_name") or result.get("file", "Review")
    summary = result.get("summary", "")
    crit = result.get("critical_count", 0)
    warn = result.get("warning_count", 0)
    info = result.get("info_count", 0)

    # Export Buttons Row
    col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 1])
    stem = file_stem(result.get("language", "project"))
    with col_dl1:
        st.download_button(
            "📥 Export Markdown Report",
            data=build_markdown(result, language=result.get("language", "Python")),
            file_name=f"{stem}.md",
            mime="text/markdown",
        )
    with col_dl2:
        st.download_button(
            "📥 Export JSON Report",
            data=build_json(result),
            file_name=f"{stem}.json",
            mime="application/json",
        )
    with col_dl3:
        st.download_button(
            "📥 Export CSV Findings",
            data=build_csv(result),
            file_name=f"{stem}_findings.csv",
            mime="text/csv",
        )

    st.write("")

    # Dedicated Tabs
    tab_overview, tab_sec, tab_bugs, tab_quality, tab_opt, tab_comp, tab_diff = st.tabs([
        "📊 Overview",
        f"🛡️ Security ({len(result.get('security_findings', []))})",
        f"🐛 Bugs & Smells ({len(result.get('bugs', []))})",
        "📈 Quality & Maintainability",
        "⚡ Optimisation",
        "🔄 Complexity",
        "🔀 Before / After Diff",
    ])

    # 1. Overview Tab
    with tab_overview:
        c1, c2 = st.columns([1.5, 1.0])
        with c1:
            st.markdown(f"### Review Summary: `{name}`")
            st.write(summary)
            st.markdown("#### Component Scores (0-10 Scale)")
            st.markdown(f"- **Security Score:** `{scores.get('security_score', 10.0)}/10` (Weight: 30%)")
            st.markdown(f"- **Correctness / Bugs:** `{scores.get('correctness_score', 10.0)}/10` (Weight: 30%)")
            st.markdown(f"- **Maintainability:** `{scores.get('maintainability_score', 8.0)}/10` (Weight: 20%)")
            st.markdown(f"- **Complexity:** `{scores.get('complexity_score', 8.0)}/10` (Weight: 20%)")
        with c2:
            st.plotly_chart(render_health_radar_chart(scores), use_container_width=True)

    # 2. Security Tab
    with tab_sec:
        sec_findings = result.get("security_findings", [])
        if not sec_findings:
            st.success("🛡️ No security vulnerabilities detected in the analyzed files.")
        else:
            col_filter, col_sort = st.columns([1, 1])
            with col_filter:
                sev_choice = st.multiselect("Filter by Severity", ["critical", "warning", "info"], default=["critical", "warning", "info"], key="sec_sev_filter")
            filtered_sec = [f for f in sec_findings if (f.get("severity") or "info").lower() in sev_choice]
            for idx, sf in enumerate(filtered_sec):
                render_finding_card(sf, index=idx)

    # 3. Bugs Tab
    with tab_bugs:
        bugs = result.get("bugs", [])
        if not bugs:
            st.success("✅ No logic bugs, syntax errors, or code smells detected.")
        else:
            col_f1, col_f2 = st.columns([1, 1])
            with col_f1:
                sev_choice_bugs = st.multiselect("Filter by Severity", ["critical", "warning", "info"], default=["critical", "warning", "info"], key="bug_sev_filter")
            with col_f2:
                sources = list({b.get("source", "static") for b in bugs})
                src_choice = st.multiselect("Filter by Source", sources, default=sources, key="bug_src_filter")

            filtered_bugs = [
                b for b in bugs
                if (b.get("severity") or "info").lower() in sev_choice_bugs
                and b.get("source", "static") in src_choice
            ]
            for idx, b in enumerate(filtered_bugs):
                render_finding_card(b, index=idx + 100)

    # 4. Quality Tab
    with tab_quality:
        st.markdown("### Code Review Scoring Formula")
        st.markdown(
            """
            TechSpecAnalyser uses a transparent four-pillar scoring methodology:
            $$\\text{Overall Score} = 0.30 \\times S_{\\text{Security}} + 0.30 \\times S_{\\text{Correctness}} + 0.20 \\times S_{\\text{Maintainability}} + 0.20 \\times S_{\\text{Complexity}}$$
            """
        )
        penalties = scores.get("penalties", [])
        if penalties:
            st.markdown("#### Applied Penalties:")
            for p in penalties:
                st.markdown(f"- ⚠️ {p}")
        else:
            st.success("No penalties deducted. Clean implementation.")

    # 5. Optimisation Tab
    with tab_opt:
        st.markdown("### Architectural Improvements & Optimization Recommendations")
        improvements = result.get("improvements", [])
        if improvements:
            for imp in improvements:
                st.markdown(f"#### 💡 {imp.get('title', 'Recommendation')}")
                st.write(imp.get("detail", ""))
                st.markdown("---")
        else:
            st.info("No explicit optimization suggestions generated for this code snippet.")

        notes = result.get("complexity_notes", "")
        if notes:
            st.markdown(f"**Complexity Analysis Note:**\n{notes}")

    # 6. Complexity Tab
    with tab_comp:
        comp_data = result.get("complexity") or {}
        st.markdown(f"### Cyclomatic Complexity & Maintainability")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Average Complexity", f"{comp_data.get('average_complexity', 1.0)}", f"Rank {comp_data.get('rating', 'A')}")
        with col_m2:
            st.metric("Maintainability Index (MI)", f"{comp_data.get('maintainability_index', 100.0)}", f"Rank {comp_data.get('maintainability_rank', 'A')}")

        blocks = comp_data.get("blocks", [])
        if blocks:
            st.plotly_chart(render_complexity_distribution(blocks), use_container_width=True)
            st.dataframe(blocks, use_container_width=True)
        else:
            st.caption("No function-level complexity breakdown available.")

    # 7. Diff Tab
    with tab_diff:
        st.markdown("### Original vs AI-Improved Implementation")
        render_code_comparison(
            original_code=result.get("reviewed_code", ""),
            improved_code=result.get("improved_code", ""),
            language=result.get("language", "python"),
        )
