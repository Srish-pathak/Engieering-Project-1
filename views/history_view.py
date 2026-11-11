"""
TechSpecAnalyser — Review History & Commit Comparison View.
Enables inspecting past review runs, diffing two sessions/commits,
and monitoring newly introduced versus resolved issues.
"""
import streamlit as st

from database.repositories import compare_two_sessions, get_recent_sessions


def render_history_view() -> None:
    """Renders Review History & Session Comparison interface."""
    st.markdown(
        """
        <div class="ts-header">
          <h1>Review History & Commit Comparison</h1>
          <p>Inspect past reviews, compare commit sessions, and track newly introduced vs resolved findings.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sessions = get_recent_sessions(limit=35)
    if not sessions:
        st.info("No past review sessions recorded in SQLite yet.")
        return

    tab_list, tab_compare = st.tabs(["📜 Review Session History", "⚖️ Compare Two Sessions / Commits"])

    with tab_list:
        st.markdown(f"**Stored Review Runs ({len(sessions)}):**")
        for s in sessions:
            sid = s.get("id", "N/A")
            name = s.get("repo_full_name") or s.get("project_name", "Review")
            time_str = s.get("time", "")
            score = s.get("overall_score", 0.0)
            crit = s.get("critical_count", 0)
            warn = s.get("warning_count", 0)
            commit = (s.get("commit_sha") or "")[:7]

            with st.container():
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                with c1:
                    st.markdown(f"**{name}** `({sid})`")
                    st.caption(f"Branch: `{s.get('branch', 'main')}` | Commit: `{commit or 'manual'}` | {time_str}")
                with c2:
                    score_col = "var(--good)" if score >= 8 else "var(--warn)" if score >= 5 else "var(--crit)"
                    st.markdown(f"Score: **<span style='color:{score_col}'>{score}/10</span>**", unsafe_allow_html=True)
                with c3:
                    st.markdown(f"🚨 {crit} crit | ⚠️ {warn} warn")
                with c4:
                    if st.button("Open Report", key=f"hist_open_{sid}"):
                        st.session_state["active_review_result"] = s
                        st.session_state["active_nav"] = "🔍 Code Review"
                        st.rerun()
                st.markdown("---")

    with tab_compare:
        st.markdown("### Compare Two Review Runs")
        session_options = {
            f"{s.get('repo_full_name', 'Repo')} - {s.get('time', '')} ({s.get('id', '')})": s.get("id")
            for s in sessions
        }

        col_base, col_target = st.columns(2)
        with col_base:
            base_choice = st.selectbox("Base (Earlier) Session", list(session_options.keys()), index=len(session_options) - 1 if len(session_options) > 1 else 0)
            base_id = session_options[base_choice]
        with col_target:
            target_choice = st.selectbox("Target (Later) Session", list(session_options.keys()), index=0)
            target_id = session_options[target_choice]

        if st.button("⚖️ Run Session Comparison", type="primary"):
            comp_result = compare_two_sessions(base_id, target_id)
            if "error" in comp_result:
                st.error(comp_result["error"])
                return

            st.markdown("---")
            delta = comp_result["score_delta"]
            delta_str = f"+{delta}" if delta > 0 else f"{delta}"
            delta_color = "var(--good)" if delta > 0 else "var(--crit)" if delta < 0 else "var(--muted)"

            st.markdown(
                f"""
                <div class="ts-metric-card" style="margin-bottom:1rem;">
                  <div class="ts-metric-label">Score Delta</div>
                  <div class="ts-metric-value" style="color:{delta_color};">{delta_str} <span style="font-size:1.1rem;">points ({comp_result['base_score']} → {comp_result['target_score']})</span></div>
                  <div class="ts-metric-sub">Resolved {comp_result['resolved_count']} issues | Introduced {comp_result['new_count']} new issues</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_res, col_new = st.columns(2)
            with col_res:
                st.markdown(f"#### ✅ Resolved Issues ({comp_result['resolved_count']})")
                for r_issue in comp_result["resolved_issues"]:
                    st.success(f"Fixed: **{r_issue.get('title', r_issue.get('rule'))}** ({r_issue.get('file')}:{r_issue.get('line')})")

            with col_new:
                st.markdown(f"#### ⚠️ Newly Introduced Issues ({comp_result['new_count']})")
                for n_issue in comp_result["new_issues"]:
                    st.error(f"New: **{n_issue.get('title', n_issue.get('rule'))}** ({n_issue.get('file')}:{n_issue.get('line')})")
