"""
TechSpecAnalyser — Performance Analytics View.
Visualizes long-term code quality, vulnerability severity, and complexity distributions.
"""
import streamlit as st

from components.charts import (
    render_health_radar_chart,
    render_quality_trend_chart,
    render_repo_issues_chart,
    render_severity_donut,
)
from database.repositories import get_dashboard_metrics


def render_analytics_view() -> None:
    """Renders Performance & Quality Analytics."""
    st.markdown(
        """
        <div class="ts-header">
          <h1>Performance & Quality Analytics</h1>
          <p>Longitudinal metrics, severity distributions, and quality trend progressions across review sessions.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics = get_dashboard_metrics()

    c1, c2 = st.columns([1.5, 1.0])
    with c1:
        st.plotly_chart(render_quality_trend_chart(metrics["quality_trends"]), use_container_width=True)
    with c2:
        st.plotly_chart(render_severity_donut(metrics["severity_distribution"]), use_container_width=True)

    c3, c4 = st.columns([1.0, 1.5])
    with c3:
        scores = {
            "security_score": max(0.0, 10.0 - metrics["critical_security_vulnerabilities"] * 1.5),
            "correctness_score": max(0.0, 10.0 - metrics["total_bugs_detected"] * 0.4),
            "maintainability_score": 8.0,
            "complexity_score": 8.0,
        }
        st.plotly_chart(render_health_radar_chart(scores), use_container_width=True)
    with c4:
        st.plotly_chart(render_repo_issues_chart(metrics["repo_issues"]), use_container_width=True)
