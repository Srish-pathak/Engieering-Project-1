"""
TechSpecAnalyser — Advanced AI-Powered Code Intelligence & Security Platform.
Primary Streamlit Application. Run with: streamlit run app.py
"""
import html
import os
import re
import streamlit as st

from complexity import analyze_complexity
from components.styles import DEVELOPER_SPACE_CSS
from config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    get_gemini_api_key,
    get_github_token,
    is_gemini_configured,
)
from report import build_html, build_json, build_markdown, file_stem, unified_diff
from reviewer import MODEL_NAME, api_key_configured, review_code
from samples import SAMPLES
from utils import (
    LANGUAGE_CONFIG,
    SEVERITY_ORDER,
    SEVERITY_STYLE,
    SOURCE_LABELS,
    add_history,
    count_by_severity,
    history_enabled,
    load_history,
    make_history_entry,
    score_band,
)
from views.add_repo_view import render_add_repo_view
from views.analytics_view import render_analytics_view
from views.assistant_view import render_assistant_view
from views.dashboard_view import render_dashboard_view
from views.history_view import render_history_view
from views.intelligence_view import render_intelligence_view
from views.projects_view import render_projects_view
from views.security_view import render_security_view
from views.settings_view import render_settings_view

try:
    from streamlit_ace import st_ace
    HAS_ACE = True
except ImportError:
    HAS_ACE = False

st.set_page_config(
    page_title=f"{APP_NAME} — Code Intelligence & Security Platform",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Developer Space Theme
st.markdown(DEVELOPER_SPACE_CSS, unsafe_allow_html=True)

RING_COLORS = {"green": "#5BD6A0", "orange": "#FFC857", "red": "#FF6B7A"}
RANK_TONE = {"A": "good", "B": "good", "C": "warning", "D": "critical", "E": "critical", "F": "critical"}


def esc(text):
    return html.escape(str(text)).replace("$", "&#36;")


def rich(text):
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(text))


def html_block(markup):
    st.markdown(re.sub(r"\n\s*", "", markup), unsafe_allow_html=True)


def score_ring(score, size=132):
    label, tone = score_band(score)
    pct = max(0, min(100, score * 10))
    return (
        f'<div class="ts-ring" style="--pct:{pct};--ring:{RING_COLORS[tone]};--size:{size}px">'
        f'<div class="ts-ring-inner"><span class="ts-ring-num">{score:g}</span>'
        f'<span class="ts-ring-den">/10 · {esc(label)}</span></div></div>'
    )


def metric_card(label, value, hint="", tone=""):
    return (
        f'<div class="ts-card ts-{tone}"><div class="k">{esc(label)}</div>'
        f'<div class="v" style="color:var(--c,var(--text))">{esc(value)}</div><div class="h">{esc(hint)}</div></div>'
    )


def bar_row(name, value, max_value, tone, extra=""):
    width = 0 if max_value <= 0 else max(3, min(100, value / max_value * 100))
    return (
        f'<div class="ts-bar-row ts-{tone}"><span class="n" title="{esc(name)}">{esc(name)}</span>'
        f'<div class="ts-bar"><span style="width:{width}%"></span></div><span class="x">{esc(extra or value)}</span></div>'
    )


# Session state initialization
ss = st.session_state
if "history" not in ss:
    ss.history = load_history()
for key, default in (
    ("result", None),
    ("complexity", None),
    ("editor_version", 0),
    ("seed_code", ""),
    ("applied", None),
    ("last_upload", None),
    ("active_nav", "🔍 Code Review"),
):
    ss.setdefault(key, default)


def reset_results():
    ss.result = None
    ss.complexity = None


def open_history_entry(entry_id):
    entry = next((e for e in ss.history if e["id"] == entry_id), None)
    if not entry:
        return
    lang = entry["language"]
    ss.language = lang
    ss.applied = (lang, ss.get(f"sample_{lang}", next(iter(SAMPLES[lang]))))
    ss.seed_code = entry["code"]
    ss.editor_version += 1
    ss.result, ss.complexity = entry["result"], entry["complexity"]


# ----------------- SIDEBAR -----------------
with st.sidebar:
    key_ok_sidebar = api_key_configured()
    ai_dot = "green" if key_ok_sidebar else "red"
    ai_label = "Gemini Active" if key_ok_sidebar else "No API Key"
    st.markdown(
        f"""
        <div style="padding: 0.5rem 0 1rem 0; border-bottom: 1px solid #263056; margin-bottom: 0.8rem;">
          <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.3rem;">
            <span style="font-size:1.6rem;">🛰️</span>
            <span class="ts-glow" style="font-family:'Space Grotesk',sans-serif; font-size:1.3rem; font-weight:700; color:#4FD1E8; letter-spacing:-0.02em;">{APP_NAME}</span>
          </div>
          <div style="display:flex; align-items:center; gap:0.4rem; margin-left:0.2rem;">
            <span class="ts-status-dot {ai_dot}"></span>
            <span style="font-size:0.75rem; color:#98A2C8;">{ai_label} · v{APP_VERSION}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Navigation Menu
    nav_options = [
        "🔍 Code Review",
        "📊 Dashboard",
        "📁 My Projects",
        "🔗 Add Repository",
        "🧠 Repository Intelligence",
        "🛡️ Security Centre",
        "💬 AI Developer Assistant",
        "📜 Review History",
        "📈 Performance Analytics",
        "⚙️ Settings & Webhooks",
    ]

    selected_nav = st.radio(
        "Platform Navigation",
        nav_options,
        index=nav_options.index(ss.active_nav) if ss.active_nav in nav_options else 0,
        label_visibility="collapsed",
    )
    ss.active_nav = selected_nav

    st.markdown("---")

    # Code Review Sidebar Controls (Language, Sample, Upload, AI Toggle, History)
    if selected_nav == "🔍 Code Review":
        language = st.selectbox("Language", list(LANGUAGE_CONFIG), key="language")
        choice = st.selectbox(
            "Load a test case",
            list(SAMPLES[language]),
            key=f"sample_{language}",
            help="Ready-made examples that show what each analyzer can detect.",
        )
        uploaded = st.file_uploader(
            f"Or upload a {LANGUAGE_CONFIG[language]['ext']} file",
            type=[LANGUAGE_CONFIG[language]["ext"].lstrip(".")],
            key=f"upload_{language}",
        )

        st.markdown("---")
        key_ok = api_key_configured()
        use_ai = st.toggle("AI review (Gemini)", value=key_ok, disabled=not key_ok)
        if key_ok:
            st.caption(f"✅ API key detected · model `{MODEL_NAME}`")
        else:
            st.warning("No `GEMINI_API_KEY` found. Local analysis still works; add the key to `.env` for AI review.")

        if ss.history and history_enabled():
            with st.expander(f"Review history ({len(ss.history)})", expanded=False):
                for item in reversed(ss.history[-10:]):
                    c_info, c_btn = st.columns([3, 2])
                    c_info.caption(f"{item['language']} · {item['time']} · score {item['result'].get('overall_score', 0)}")
                    if c_btn.button("Open review", key=f"open_{item['id']}", on_click=open_history_entry, args=(item["id"],)):
                        pass

        if not history_enabled():
            st.caption("History saving is turned off on this server.")

        # Load selected sample / file
        if ss.applied != (language, choice):
            ss.applied = (language, choice)
            ss.seed_code = SAMPLES[language][choice]
            ss.editor_version += 1
            reset_results()
        if uploaded is not None:
            token = (language, uploaded.name, uploaded.size)
            if ss.last_upload != token:
                ss.last_upload = token
                ss.seed_code = uploaded.getvalue().decode("utf-8", errors="replace")
                ss.editor_version += 1
                reset_results()

    else:
        # Generic Sidebar Information
        key_ok = api_key_configured()
        if key_ok:
            st.markdown(
                '<div style="background:rgba(91,214,160,0.15); border:1px solid #5BD6A0; border-radius:6px; padding:0.3rem 0.6rem; font-size:0.82rem; color:#5BD6A0;">'
                '🟢 <strong>Gemini AI Active</strong>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("No `GEMINI_API_KEY` found. Add the key in Settings or `.env` for AI capabilities.")

        active_res = ss.get("active_review_result")
        if active_res:
            rname = active_res.get("repo_full_name") or active_res.get("project_name") or "Session"
            st.markdown(
                f"""
                <div style="background:#131A33; border:1px solid #263056; border-radius:6px; padding:0.6rem 0.8rem; font-size:0.82rem; margin-top:0.8rem;">
                  <div style="color:#98A2C8; font-size:0.75rem;">ACTIVE REPOSITORY</div>
                  <div style="color:#E7EBFA; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{rname}</div>
                  <div style="color:#4FD1E8; margin-top:0.2rem;">Score: <strong>{active_res.get('overall_score', 0)}/10</strong></div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ----------------- PAGE ROUTER -----------------
if selected_nav == "📊 Dashboard":
    render_dashboard_view()

elif selected_nav == "📁 My Projects":
    render_projects_view()

elif selected_nav == "🔗 Add Repository":
    render_add_repo_view()

elif selected_nav == "🧠 Repository Intelligence":
    render_intelligence_view()

elif selected_nav == "🛡️ Security Centre":
    render_security_view()

elif selected_nav == "💬 AI Developer Assistant":
    render_assistant_view()

elif selected_nav == "📜 Review History":
    render_history_view()

elif selected_nav == "📈 Performance Analytics":
    render_analytics_view()

elif selected_nav == "⚙️ Settings & Webhooks":
    render_settings_view()

elif selected_nav == "🔍 Code Review":
    # Hero Title (preserves both TechSpecAnalyser and legacy TecSpace Analyser text)
    html_block(
        f"""<div class="ts-hero"><h1>{APP_NAME} <span style="font-size:1.1rem; color:var(--muted); font-weight:normal;">(TecSpace Analyser)</span></h1>
        <p>Your Intelligent AI-Powered Code Review, Security & Repository Intelligence Platform.</p>
        <div class="ts-stages"><span class="ts-stage">Syntax check</span><span class="ts-stage">Static analysis</span>
        <span class="ts-stage">Measured complexity</span><span class="ts-stage">Gemini review</span>
        <span class="ts-stage">Quality score</span></div></div>"""
    )

    st.subheader("Your code")
    editor_key = f"editor_{ss.editor_version}"
    if HAS_ACE:
        code_input = st_ace(
            value=ss.seed_code,
            language=LANGUAGE_CONFIG[language]["ace_mode"],
            theme="tomorrow_night",
            font_size=14,
            height=340,
            wrap=True,
            auto_update=True,
            key=editor_key,
        )
    else:
        code_input = st.text_area("Paste code here", value=ss.seed_code, height=340, key=editor_key)
    code_input = code_input or ""

    col_run, col_clear, _ = st.columns([2, 2, 6])
    run_clicked = col_run.button("Analyze code", type="primary")
    if col_clear.button("Clear results"):
        reset_results()
        st.rerun()

    if run_clicked:
        if not code_input.strip():
            st.warning("The editor is empty. Paste some code or load a test case first.")
        else:
            with st.status("Analyzing your code…", expanded=True) as status:
                complexity = analyze_complexity(code_input, language)
                st.write("✔ Measured complexity")
                result = review_code(
                    code_input,
                    language,
                    complexity,
                    use_ai=use_ai,
                    progress=lambda message: st.write(f"• {message}…"),
                )
                status.update(label="Analysis complete", state="complete", expanded=False)
            ss.result, ss.complexity = result, complexity
            ss.active_review_result = result
            if not result.get("error"):
                ss.history = add_history(
                    ss.history,
                    make_history_entry(language, code_input, result, complexity),
                )

    # Render review results if available
    result, complexity = ss.result, ss.complexity
    if result is not None:
        st.markdown("---")
        tabs = st.tabs(["Summary", "Issues", "Improvements", "Complexity", "Improved code", "Diff", "Export"])

        with tabs[0]:
            bugs = result.get("bugs", [])
            counts = count_by_severity(bugs)
            score = result.get("overall_score", 0)
            cx_value = complexity["rating"] if complexity else "N/A"
            cx_hint = f"{complexity['analysis_type']} · avg {complexity['average_complexity']}" if complexity else ""
            mi = complexity.get("maintainability_index") if complexity else None

            html_block(
                f"""<div class="ts-summary">{score_ring(score)}<div class="ts-cards">
                {metric_card("Critical", counts["critical"], "must fix", "critical" if counts["critical"] else "good")}
                {metric_card("Warnings", counts["warning"], "should fix", "warning" if counts["warning"] else "good")}
                {metric_card("Info", counts["info"], "nice to fix", "info")}
                {metric_card("Complexity", cx_value, cx_hint, RANK_TONE.get(cx_value, ""))}
                {metric_card("Maintainability", "N/A" if mi is None else mi, "Python only" if mi is None else (complexity["mi_label"]), "good" if mi is not None else "")}
                </div></div>"""
            )

            if result.get("ai_status") == "failed":
                st.warning(f"AI review unavailable: {result['ai_error']}\n\nSyntax, static and complexity results below are still valid.")
            if result.get("summary"):
                st.info(result["summary"])

            left, right = st.columns(2)
            with left:
                st.markdown("**Issues by severity**")
                top = max(counts.values()) or 1
                html_block("".join(bar_row(SEVERITY_STYLE[s]["label"], counts[s], top, s) for s in SEVERITY_ORDER))
            with right:
                st.markdown("**Complexity by function**")
                rows = (complexity or {}).get("details") or []
                if rows:
                    top = max(20, max(r["complexity"] for r in rows))
                    html_block("".join(
                        bar_row(r["name"], r["complexity"], top, RANK_TONE.get(r["rank"], "info"), f"{r['complexity']} · {r['rank']}")
                        for r in rows[:8]
                    ))
                else:
                    st.caption("No function-level data for this code.")

            st.markdown("**What ran**")
            syntax_errors = [b for b in bugs if b.get("source") in ("syntax", "g++")]
            static_n = len([b for b in bugs if b.get("source") == "static"])
            ai_status = result.get("ai_status")
            cards = [
                ("Syntax check", "Failed" if syntax_errors else "Passed", result.get("checker") or "", "critical" if syntax_errors else "good"),
                ("Static analysis", "Skipped" if syntax_errors else f"{static_n} finding(s)", "rule based, no AI", "info" if syntax_errors else ("warning" if static_n else "good")),
                ("Complexity", (complexity or {}).get("analysis_type", "n/a").title(), (complexity or {}).get("method", ""), "good" if (complexity or {}).get("analysis_type") == "measured" else "warning"),
                ("AI review", {"ok": "Done", "failed": "Failed", "skipped": "Skipped"}.get(ai_status, "n/a"), result.get("model") or "", {"ok": "good", "failed": "critical"}.get(ai_status, "info")),
            ]
            html_block(
                '<div class="ts-cards">' + "".join(
                    f'<div class="ts-stagecard ts-{tone}"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div><div class="h">{esc(h)}</div></div>'
                    for k, v, h, tone in cards
                ) + "</div>"
            )

        with tabs[1]:
            bugs = result.get("bugs", [])
            if not bugs:
                st.success("No issues found. Nice and clean ✅")
            else:
                shown = st.multiselect(
                    "Show severities",
                    SEVERITY_ORDER,
                    default=SEVERITY_ORDER,
                    format_func=lambda s: SEVERITY_STYLE[s]["label"],
                )
                source_lines = result.get("reviewed_code", "").splitlines()
                for bug in bugs:
                    if bug["severity"] not in shown:
                        continue
                    style = SEVERITY_STYLE[bug["severity"]]
                    line = bug.get("line", "N/A")
                    snippet = ""
                    if str(line).isdigit() and 1 <= int(line) <= len(source_lines):
                        snippet = f'<code class="ts-snippet">{esc(source_lines[int(line) - 1].rstrip())}</code>'
                    fix = f'<div class="ts-fix"><strong>Fix:</strong> {rich(bug["fix"])}</div>' if bug.get("fix") else ""
                    html_block(
                        f"""<div class="ts-issue ts-{bug['severity']}"><div class="ts-issue-head">
                        <span class="ts-pill">{style['label']}</span><span>Line {esc(line)}</span>
                        <span>{esc(SOURCE_LABELS.get(bug.get('source'), bug.get('source', '')))}</span></div>
                        <div>{rich(bug['description'])}</div>{snippet}{fix}</div>"""
                    )

        with tabs[2]:
            items = result.get("improvements", [])
            if not items:
                st.info("No improvement suggestions. Turn on AI review to get them." if result.get("ai_status") != "ok" else "No specific improvements suggested.")
            for item in items:
                html_block(f'<div class="ts-tip"><h4>💡 {esc(item["title"])}</h4><div>{rich(item["detail"])}</div></div>')

        with tabs[3]:
            if not complexity:
                st.info("Run an analysis to see complexity.")
            else:
                st.markdown(f"**Average cyclomatic complexity:** `{complexity['average_complexity']}` · rating **{complexity['rating']}**")
                rows = complexity.get("details", [])
                if rows:
                    st.dataframe(rows, use_container_width=True)

        with tabs[4]:
            improved = result.get("improved_code", "")
            if not improved:
                st.info("No improved code returned. AI review is either switched off or unavailable.")
            else:
                if result.get("improved_code_valid") is True:
                    st.success("The improved code passed the syntax and static checks.")
                elif result.get("improved_code_valid") is False:
                    st.warning("The improved code returned with potential issues:")
                    for iss in result.get("improved_code_issues", []):
                        st.write(f"- {iss}")
                st.code(improved, language=LANGUAGE_CONFIG[language]["ace_mode"])

        with tabs[5]:
            improved = result.get("improved_code", "")
            if not improved:
                st.info("The diff appears once an improved version is generated.")
            else:
                diff_text = unified_diff(result.get("reviewed_code", ""), improved)
                if diff_text:
                    st.code(diff_text, language="diff")
                else:
                    st.success("Original and improved code are identical.")

        with tabs[6]:
            st.markdown("### Export review reports")
            stem = file_stem(language)
            c1, c2, c3 = st.columns(3)
            c1.download_button("Markdown (.md)", data=build_markdown(result, complexity, code_input, language), file_name=f"{stem}.md", mime="text/markdown")
            c2.download_button("HTML standalone (.html)", data=build_html(result, complexity, code_input, language), file_name=f"{stem}.html", mime="text/html")
            c3.download_button("JSON data (.json)", data=build_json(result, complexity, code_input, language), file_name=f"{stem}.json", mime="application/json")
