"""
TechSpecAnalyser — My Projects View.
Lists all connected and analyzed GitHub repositories from SQLite,
enables re-scanning, commit comparisons, and report reopening.
"""
import streamlit as st

from database.db import get_db_connection
from database.repositories import get_recent_sessions


def render_projects_view() -> None:
    """Renders the My Projects management interface."""
    st.markdown(
        """
        <div class="ts-header">
          <h1>My Projects & Repositories</h1>
          <p>Manage tracked repositories, view historical score progressions, and trigger manual re-scans.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with get_db_connection() as conn:
        repos = conn.execute(
            """
            SELECT p.project_id, p.name, p.repo_url, p.default_branch, p.updated_at,
                   COUNT(s.id) as review_count,
                   AVG(s.overall_score) as avg_score,
                   MAX(s.created_at) as last_reviewed
            FROM projects p
            LEFT JOIN review_sessions s ON p.project_id = s.project_id OR p.name = s.repo_full_name
            GROUP BY p.project_id
            ORDER BY p.updated_at DESC
            """
        ).fetchall()

    if not repos:
        st.info("No projects registered yet. Go to **Add Repository** to connect your first GitHub project.")
        if st.button("➕ Connect a Repository"):
            st.session_state["active_nav"] = "🔗 Add Repository"
            st.rerun()
        return

    for r in repos:
        name = r["name"]
        score = round(r["avg_score"] or 0.0, 1)
        count = r["review_count"]
        last_date = r["last_reviewed"] or r["updated_at"]
        url = r["repo_url"] or ""

        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"### 📦 {name}")
                if url:
                    st.markdown(f"[View on GitHub]({url}) | Default branch: `{r['default_branch']}`")
            with col2:
                st.metric("Avg Quality Score", f"{score}/10", f"{count} reviews")
            with col3:
                st.caption(f"Last analyzed: {last_date}")
                if st.button("Open Latest Report", key=f"open_{r['project_id']}"):
                    sessions = get_recent_sessions(limit=50)
                    matching = [s for s in sessions if s.get("repo_full_name") == name or s.get("project_name") == name]
                    if matching:
                        st.session_state["active_review_result"] = matching[0]
                        st.session_state["active_nav"] = "🔍 Code Review"
                        st.rerun()
                    else:
                        st.warning("No detailed session payload found for this project.")
            st.markdown("---")
