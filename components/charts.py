"""
TechSpecAnalyser — Plotly Visualization Engine.
Generates interactive, responsive charts themed for the Developer Space aesthetic.
"""
from typing import Any, Dict, List

import plotly.express as px
import plotly.graph_objects as go

# Developer Space Theme Colors
THEME_BG = "#0B1020"
PANEL_BG = "#131A33"
GRID_COLOR = "#263056"
TEXT_COLOR = "#E7EBFA"
MUTED_COLOR = "#98A2C8"
ACCENT_BLUE = "#4FD1E8"
VIOLET = "#9D7BFF"
CRIMSON = "#FF6B7A"
AMBER = "#FFC857"
EMERALD = "#5BD6A0"


def render_quality_trend_chart(trends: List[Dict[str, Any]]) -> go.Figure:
    """Builds a code quality score trend line over historical reviews."""
    if not trends:
        fig = go.Figure()
        fig.add_annotation(text="No review history recorded yet.", showarrow=False, font=dict(color=MUTED_COLOR, size=14))
        _apply_theme(fig, "Code Quality Trend Over Time")
        return fig

    x_labels = [f"#{idx+1} {t.get('created_at', '')[:10]}" for idx, t in enumerate(trends)]
    y_scores = [t.get("overall_score", 0.0) for t in trends]
    repos = [t.get("repo_full_name", "") for t in trends]

    fig = go.Figure()
    # Quality line
    fig.add_trace(go.Scatter(
        x=x_labels,
        y=y_scores,
        mode="lines+markers",
        name="Quality Score",
        line=dict(color=ACCENT_BLUE, width=3),
        marker=dict(size=8, color=VIOLET, line=dict(color=ACCENT_BLUE, width=2)),
        text=[f"Repo: {r}<br>Score: {s}/10" for r, s in zip(repos, y_scores)],
        hoverinfo="text",
    ))

    # Reference quality bands
    fig.add_hrect(y0=8.0, y1=10.0, fillcolor=EMERALD, opacity=0.08, line_width=0, annotation_text="Production Ready (8-10)", annotation_position="top left")
    fig.add_hrect(y0=5.0, y1=8.0, fillcolor=AMBER, opacity=0.08, line_width=0, annotation_text="Acceptable with Warnings (5-8)", annotation_position="top left")
    fig.add_hrect(y0=0.0, y1=5.0, fillcolor=CRIMSON, opacity=0.08, line_width=0, annotation_text="Critical Action Required (0-5)", annotation_position="bottom left")

    fig.update_yaxes(range=[0, 10.5], dtick=2)
    _apply_theme(fig, "Code Quality Score Trend (0-10)")
    return fig


def render_severity_donut(severity_counts: Dict[str, int]) -> go.Figure:
    """Builds a security & bug finding severity distribution donut chart."""
    labels = ["Critical", "Warning", "Info"]
    values = [
        severity_counts.get("critical", 0),
        severity_counts.get("warning", 0) + severity_counts.get("high", 0),
        severity_counts.get("info", 0) + severity_counts.get("low", 0),
    ]

    colors = [CRIMSON, AMBER, ACCENT_BLUE]

    if sum(values) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No findings detected — Clean codebase!", showarrow=False, font=dict(color=EMERALD, size=14))
        _apply_theme(fig, "Findings by Severity")
        return fig

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=PANEL_BG, width=2)),
        textinfo="label+value",
        hoverinfo="label+value+percent",
    )])

    _apply_theme(fig, "Security & Bug Findings by Severity")
    return fig


def render_health_radar_chart(scores: Dict[str, float]) -> go.Figure:
    """Builds a 4-pillar repository health radar chart."""
    categories = ["Security", "Correctness", "Maintainability", "Complexity"]
    values = [
        scores.get("security_score", 10.0),
        scores.get("correctness_score", 10.0),
        scores.get("maintainability_score", 10.0),
        scores.get("complexity_score", 10.0),
    ]
    # Close the polygon loop
    categories_loop = categories + [categories[0]]
    values_loop = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_loop,
        theta=categories_loop,
        fill="toself",
        fillcolor="rgba(79, 209, 232, 0.25)",
        line=dict(color=ACCENT_BLUE, width=2),
        name="Health Score",
    ))

    fig.update_layout(
        polar=dict(
            bgcolor=PANEL_BG,
            radialaxis=dict(visible=True, range=[0, 10], gridcolor=GRID_COLOR, tickfont=dict(color=MUTED_COLOR)),
            angularaxis=dict(gridcolor=GRID_COLOR, tickfont=dict(color=TEXT_COLOR, size=12)),
        ),
        paper_bgcolor=THEME_BG,
        plot_bgcolor=THEME_BG,
        margin=dict(l=40, r=40, t=50, b=40),
        title=dict(text="Repository Health Pillars (0-10)", font=dict(color=TEXT_COLOR, size=15)),
        showlegend=False,
    )
    return fig


def render_repo_issues_chart(repo_issues: List[Dict[str, Any]]) -> go.Figure:
    """Builds horizontal bar chart for issues per repository."""
    if not repo_issues:
        fig = go.Figure()
        fig.add_annotation(text="No repository data available.", showarrow=False, font=dict(color=MUTED_COLOR, size=14))
        _apply_theme(fig, "Issues per Repository")
        return fig

    repos = [r.get("repo_full_name", "") for r in repo_issues][:8]
    counts = [r.get("issue_count", 0) for r in repo_issues][:8]

    fig = go.Figure(go.Bar(
        x=counts,
        y=repos,
        orientation="h",
        marker=dict(color=VIOLET, line=dict(color=ACCENT_BLUE, width=1)),
    ))

    _apply_theme(fig, "Issues by Repository")
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return fig


def render_complexity_distribution(blocks: List[Dict[str, Any]]) -> go.Figure:
    """Builds function complexity distribution bar chart."""
    if not blocks:
        fig = go.Figure()
        fig.add_annotation(text="No function complexity data.", showarrow=False, font=dict(color=MUTED_COLOR, size=14))
        _apply_theme(fig, "Cyclomatic Complexity Distribution")
        return fig

    names = [b.get("name", "func") for b in blocks[:15]]
    ccs = [b.get("complexity", 1) for b in blocks[:15]]
    colors = [EMERALD if cc <= 5 else AMBER if cc <= 10 else CRIMSON for cc in ccs]

    fig = go.Figure(go.Bar(
        x=names,
        y=ccs,
        marker=dict(color=colors),
        text=ccs,
        textposition="auto",
    ))

    _apply_theme(fig, "Top Function Cyclomatic Complexity")
    fig.update_yaxes(title_text="Cyclomatic Complexity (McCabe)")
    return fig


def _apply_theme(fig: go.Figure, title_text: str) -> None:
    """Applies consistent dark space theme styling to a Plotly figure."""
    fig.update_layout(
        title=dict(text=title_text, font=dict(color=TEXT_COLOR, size=15, family="Space Grotesk")),
        paper_bgcolor=THEME_BG,
        plot_bgcolor=PANEL_BG,
        font=dict(color=TEXT_COLOR, family="Space Grotesk, sans-serif"),
        xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, tickfont=dict(color=MUTED_COLOR)),
        yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, tickfont=dict(color=MUTED_COLOR)),
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(font=dict(color=TEXT_COLOR)),
    )
