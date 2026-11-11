"""
TechSpecAnalyser — Main Dashboard View.
Renders real-time developer workspace metrics, health radar,
quality trends, and recent commit activities from SQLite.
"""
import streamlit as st

from components.charts import (
    render_health_radar_chart,
    render_quality_trend_chart,
    render_repo_issues_chart,
    render_severity_donut,
)
from config import APP_NAME, APP_TAGLINE, is_gemini_configured
from database.repositories import get_dashboard_metrics


def render_dashboard_view() -> None:
    """Renders the Developer Space Dashboard."""
    # Header
    st.markdown(
        f"""
        <div class="ts-header">
          <h1>{APP_NAME} Developer Dashboard</h1>
          <p>{APP_TAGLINE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Load REAL metrics from SQLite
    metrics = get_dashboard_metrics()

    # Metric Cards Grid — Row 1
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""
            <div class="ts-metric-card">
              <div class="ts-metric-label">📁 Repositories</div>
              <div class="ts-metric-value">{metrics['connected_repositories']}</div>
              <div class="ts-metric-sub">{metrics['total_sessions']} Total Reviews</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="ts-metric-card">
              <div class="ts-metric-label">🔎 Files Analyzed</div>
              <div class="ts-metric-value">{metrics['total_files_reviewed']}</div>
              <div class="ts-metric-sub">Multi-Language Parsed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c3:
        avg_score = metrics["average_quality_score"]
        score_color = "var(--good)" if avg_score >= 8 else "var(--warn)" if avg_score >= 5 else "var(--crit)"
        st.markdown(
            f"""
            <div class="ts-metric-card">
              <div class="ts-metric-label">⭐ Avg Quality Score</div>
              <div class="ts-metric-value" style="color: {score_color};">{avg_score}<span style="font-size:1.1rem; color:var(--muted)">/10</span></div>
              <div class="ts-metric-sub">4-Pillar Weighted Score</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"""
            <div class="ts-metric-card">
              <div class="ts-metric-label">🛡️ Critical Security</div>
              <div class="ts-metric-value" style="color: var(--crit);">{metrics['critical_security_vulnerabilities']}</div>
              <div class="ts-metric-sub">{metrics['total_bugs_detected']} Total Bugs Detected</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # Metric Cards Grid — Row 2
    r1, r2, r3, r4 = st.columns(4)
    high_count = metrics.get("high_count", 0)
    medium_count = metrics.get("medium_count", 0)
    low_count = metrics.get("low_count", 0)
    total_sessions = metrics.get("total_sessions", 0)
    with r1:
        st.markdown(
            f"""
            <div class="ts-metric-card" style="border-left: 3px solid var(--crit);">
              <div class="ts-metric-label">🔴 High Issues</div>
              <div class="ts-metric-value" style="color: var(--crit);">{high_count}</div>
              <div class="ts-metric-sub">High severity findings</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with r2:
        st.markdown(
            f"""
            <div class="ts-metric-card" style="border-left: 3px solid var(--warn);">
              <div class="ts-metric-label">🟡 Medium Issues</div>
              <div class="ts-metric-value" style="color: var(--warn);">{medium_count}</div>
              <div class="ts-metric-sub">Medium severity findings</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with r3:
        st.markdown(
            f"""
            <div class="ts-metric-card" style="border-left: 3px solid var(--info);">
              <div class="ts-metric-label">🔵 Low Issues</div>
              <div class="ts-metric-value" style="color: var(--info);">{low_count}</div>
              <div class="ts-metric-sub">Low severity findings</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with r4:
        st.markdown(
            f"""
            <div class="ts-metric-card" style="border-left: 3px solid var(--good);">
              <div class="ts-metric-label">📋 Avg Sessions</div>
              <div class="ts-metric-value" style="color: var(--good);">{total_sessions}</div>
              <div class="ts-metric-sub">Total review sessions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Visualizations Row 1
    col_trend, col_donut = st.columns([1.6, 1.0])
    with col_trend:
        st.plotly_chart(render_quality_trend_chart(metrics["quality_trends"]), use_container_width=True)
    with col_donut:
        st.plotly_chart(render_severity_donut(metrics["severity_distribution"]), use_container_width=True)

    # Visualizations Row 2
    col_radar, col_issues = st.columns([1.2, 1.4])
    with col_radar:
        scores = {
            "security_score": max(0.0, 10.0 - metrics["critical_security_vulnerabilities"] * 2.0),
            "correctness_score": max(0.0, 10.0 - metrics["total_bugs_detected"] * 0.5),
            "maintainability_score": 8.5,
            "complexity_score": 8.0,
        }
        st.plotly_chart(render_health_radar_chart(scores), use_container_width=True)
    with col_issues:
        st.plotly_chart(render_repo_issues_chart(metrics["repo_issues"]), use_container_width=True)

    # Recent Activity Table
    st.subheader("Latest Review Activity")
    recent = metrics["recent_activity"]
    if recent:
        table_rows = []
        for r in recent:
            cid = (r.get("commit_sha") or "")[:7]
            commit_display = f"`{cid}`" if cid else "Manual"
            score = r.get("overall_score", 0.0)
            score_pill = f"**{score}/10**"
            table_rows.append({
                "Repository": r.get("repo_full_name", ""),
                "Branch": r.get("branch", "main"),
                "Commit": commit_display,
                "Score": score_pill,
                "Critical Issues": r.get("critical_count", 0),
                "Warnings": r.get("warning_count", 0),
                "Reviewed At": r.get("created_at", ""),
            })
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No reviews recorded yet. Connect a GitHub repository or paste code to begin.")
