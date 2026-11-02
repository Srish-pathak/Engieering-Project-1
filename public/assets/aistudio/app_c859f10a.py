"""TecSpace Analyser - Streamlit dashboard (run with: streamlit run app.py)."""
import html
import re

import pandas as pd
import streamlit as st

from complexity import analyze_complexity
from report import build_html, build_json, build_markdown, file_stem, unified_diff
from reviewer import MODEL_NAME, api_key_configured, review_code
from samples import SAMPLES
from utils import (
    APP_NAME,
    LANGUAGE_CONFIG,
    SEVERITY_ORDER,
    SEVERITY_STYLE,
    SOURCE_LABELS,
    add_history,
    clear_history,
    count_by_severity,
    history_enabled,
    load_history,
    make_history_entry,
    score_band,
)

try:
    from streamlit_ace import st_ace

    HAS_ACE = True
except ImportError:
    HAS_ACE = False

st.set_page_config(page_title=APP_NAME, page_icon="🛰️", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
:root{--bg:#0B1020;--panel:#131A33;--panel2:#1A2347;--line:#263056;--text:#E7EBFA;--muted:#98A2C8;
--accent:#4FD1E8;--crit:#FF6B7A;--warn:#FFC857;--info:#7AA7FF;--good:#5BD6A0;}
h1,h2,h3,.ts-display{font-family:'Space Grotesk',system-ui,sans-serif !important;letter-spacing:-0.01em}
code,pre,.ts-mono{font-family:'JetBrains Mono',ui-monospace,Consolas,monospace !important}
.block-container{padding-top:2.2rem;max-width:1220px}
.stButton>button,.stDownloadButton>button{width:100%;border-radius:8px;font-weight:600}
.stTabs [data-baseweb="tab-list"]{gap:.25rem;flex-wrap:wrap}
.stTabs [data-baseweb="tab"]{height:2.6rem;padding:0 .9rem}

.ts-hero{border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;background:var(--panel);
  padding:1.2rem 1.5rem;margin-bottom:1.2rem}
.ts-hero h1{margin:0;font-size:2.1rem;line-height:1.15}
.ts-hero p{margin:.35rem 0 0;color:var(--muted);max-width:60ch}
.ts-stages{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.9rem}
.ts-stage{border:1px solid var(--line);border-radius:999px;padding:.2rem .75rem;font-size:.82rem;color:var(--muted)}

.ts-summary{display:flex;flex-wrap:wrap;gap:1rem;align-items:stretch;margin:.4rem 0 1rem}
.ts-ring{width:var(--size,132px);height:var(--size,132px);border-radius:50%;flex:none;display:grid;place-items:center;
  background:conic-gradient(var(--ring) calc(var(--pct)*1%),#232C58 0)}
.ts-ring-inner{width:calc(var(--size,132px) - 24px);height:calc(var(--size,132px) - 24px);border-radius:50%;
  background:var(--bg);display:flex;flex-direction:column;align-items:center;justify-content:center}
.ts-ring-num{font-family:'Space Grotesk',sans-serif;font-size:2.2rem;font-weight:700;line-height:1}
.ts-ring-den{color:var(--muted);font-size:.8rem}
.ts-cards{flex:1;min-width:260px;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.7rem}
.ts-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:.8rem 1rem}
.ts-card .k{color:var(--muted);font-size:.8rem}
.ts-card .v{font-family:'Space Grotesk',sans-serif;font-size:1.7rem;font-weight:700;line-height:1.2}
.ts-card .h{color:var(--muted);font-size:.78rem;margin-top:.1rem}
.ts-critical{--c:var(--crit)}.ts-warning{--c:var(--warn)}.ts-info{--c:var(--info)}.ts-good{--c:var(--good)}

.ts-issue{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--c);border-radius:8px;
  padding:.75rem 1rem;margin-bottom:.65rem}
.ts-issue-head{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;margin-bottom:.35rem;font-size:.82rem;color:var(--muted)}
.ts-pill{background:color-mix(in srgb,var(--c) 18%,transparent);color:var(--c);border-radius:999px;padding:.05rem .65rem;
  font-weight:600;font-size:.78rem}
.ts-snippet{display:block;margin:.4rem 0 0;padding:.35rem .6rem;background:#0A0F22;border-radius:6px;font-size:.82rem;
  color:#C9D3F5;overflow-x:auto;white-space:pre}
.ts-fix{margin-top:.45rem;color:#BFE9D8;font-size:.92rem}
.ts-issue code,.ts-tip code{background:#0A0F22;padding:.05rem .35rem;border-radius:4px}
.ts-tip{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:.75rem 1rem;margin-bottom:.65rem}
.ts-tip h4{margin:0 0 .25rem;font-family:'Space Grotesk',sans-serif;font-size:1rem}

.ts-bar-row{display:flex;align-items:center;gap:.7rem;margin:.35rem 0;font-size:.88rem}
.ts-bar-row .n{width:9.5rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ts-bar{flex:1;height:.7rem;background:#232C58;border-radius:999px;overflow:hidden}
.ts-bar>span{display:block;height:100%;background:var(--c);border-radius:999px}
.ts-bar-row .x{width:4.5rem;text-align:right;color:var(--muted)}

.ts-badge{display:inline-block;border-radius:6px;padding:.15rem .6rem;font-size:.82rem;font-weight:600;
  background:color-mix(in srgb,var(--c) 18%,transparent);color:var(--c)}
.ts-stagecard{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:.7rem .9rem}
.ts-stagecard .k{color:var(--muted);font-size:.78rem}
.ts-stagecard .v{font-weight:600;color:var(--c)}
.ts-stagecard .h{color:var(--muted);font-size:.78rem}
@media (max-width:760px){.ts-hero h1{font-size:1.55rem}.ts-ring{--size:112px}.ts-bar-row .n{width:6.5rem}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

RING_COLORS = {"green": "#5BD6A0", "orange": "#FFC857", "red": "#FF6B7A"}
RANK_TONE = {"A": "good", "B": "good", "C": "warning", "D": "critical", "E": "critical", "F": "critical"}


# ------------------------------------------------------------------ small HTML helpers
def esc(text):
    # "$" is escaped too, otherwise Streamlit's markdown may treat code like `$x` as LaTeX
    return html.escape(str(text)).replace("$", "&#36;")


def rich(text):
    """Escape text, then turn `backticks` into <code> so descriptions stay readable and safe."""
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


# ------------------------------------------------------------------ session state
ss = st.session_state
if "history" not in ss:
    ss.history = load_history()
for key, default in (("result", None), ("complexity", None), ("editor_version", 0), ("seed_code", ""),
                     ("applied", None), ("last_upload", None)):
    ss.setdefault(key, default)


def reset_results():
    ss.result = None
    ss.complexity = None


def open_history_entry(entry_id):
    """Button callback: reload an earlier review (runs BEFORE the page redraws)."""
    entry = next((e for e in ss.history if e["id"] == entry_id), None)
    if not entry:
        return
    lang = entry["language"]
    ss.language = lang
    ss.applied = (lang, ss.get(f"sample_{lang}", next(iter(SAMPLES[lang]))))
    ss.seed_code = entry["code"]
    ss.editor_version += 1
    ss.result, ss.complexity = entry["result"], entry["complexity"]


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown(f"### 🛰️ {APP_NAME}")
    language = st.selectbox("Language", list(LANGUAGE_CONFIG), key="language")
    choice = st.selectbox("Load a test case", list(SAMPLES[language]), key=f"sample_{language}",
                          help="Ready-made examples that show what each analyzer can detect.")
    uploaded = st.file_uploader(f"Or upload a {LANGUAGE_CONFIG[language]['ext']} file",
                                type=[LANGUAGE_CONFIG[language]["ext"].lstrip(".")], key=f"upload_{language}")

    st.markdown("---")
    key_ok = api_key_configured()
    use_ai = st.toggle("AI review (Gemini)", value=key_ok, disabled=not key_ok)
    if key_ok:
        st.caption(f"✅ API key detected · model `{MODEL_NAME}`")
    else:
        st.warning("No `GEMINI_API_KEY` found. Local analysis still works; add the key to `.env` for AI review.")

    with st.expander("How it works"):
        st.markdown(
            "1. **Syntax check** finds code that cannot run.\n"
            "2. **Static analysis** applies rules to the syntax tree, with no AI involved.\n"
            "3. **Complexity** is measured with radon (Python) or lizard (C++/Java).\n"
            "4. **Gemini** explains problems and writes improved code.\n"
            "5. The **score** blends rule-based penalties (60%) with the AI opinion (40%)."
        )
    if not history_enabled():
        st.caption("History saving is turned off on this server.")

# load a sample / uploaded file into the editor
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

# ------------------------------------------------------------------ header
html_block(
    f"""<div class="ts-hero"><h1>{APP_NAME}</h1>
    <p>Find bugs, measure complexity and get an improved version of your Python, C++ or Java code.</p>
    <div class="ts-stages"><span class="ts-stage">Syntax check</span><span class="ts-stage">Static analysis</span>
    <span class="ts-stage">Measured complexity</span><span class="ts-stage">Gemini review</span>
    <span class="ts-stage">Quality score</span></div></div>"""
)

# ------------------------------------------------------------------ editor
st.subheader("Your code")
editor_key = f"editor_{ss.editor_version}"
if HAS_ACE:
    code_input = st_ace(
        value=ss.seed_code, language=LANGUAGE_CONFIG[language]["ace_mode"], theme="tomorrow_night",
        font_size=14, height=340, wrap=True, auto_update=True, key=editor_key,
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
            result = review_code(code_input, language, complexity, use_ai=use_ai,
                                 progress=lambda message: st.write(f"• {message}…"))
            status.update(label="Analysis complete", state="complete", expanded=False)
        ss.result, ss.complexity = result, complexity
        if not result.get("error"):
            ss.history = add_history(ss.history, make_history_entry(language, code_input, result, complexity))


# ------------------------------------------------------------------ result sections
def render_overview(result, complexity):
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


def render_issues(result):
    bugs = result.get("bugs", [])
    if not bugs:
        st.success("No issues found. Nice and clean ✅")
        return
    shown = st.multiselect("Show severities", SEVERITY_ORDER, default=SEVERITY_ORDER,
                           format_func=lambda s: SEVERITY_STYLE[s]["label"])
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


def render_improvements(result):
    items = result.get("improvements", [])
    if not items:
        st.info("No improvement suggestions. Turn on AI review to get them." if result.get("ai_status") != "ok"
                else "No specific improvements suggested.")
        return
    for item in items:
        html_block(f'<div class="ts-tip"><h4>💡 {esc(item["title"])}</h4><div>{rich(item["detail"])}</div></div>')


def render_complexity(result, complexity):
    if not complexity:
        st.info("Run an analysis to see complexity.")
        return
    if complexity.get("error"):
        st.warning(complexity["error"])
    measured = complexity["analysis_type"] == "measured"
    tone = "good" if measured else "warning"
    html_block(
        f'<span class="ts-badge ts-{tone}">{"MEASURED" if measured else "ESTIMATED"} · {esc(complexity["method"])}</span>'
    )
    st.caption(complexity["note"])
    mi = complexity.get("maintainability_index")
    html_block(
        f"""<div class="ts-cards" style="margin:.8rem 0">
        {metric_card("Average complexity", complexity["average_complexity"], complexity["rating_label"], RANK_TONE.get(complexity["rating"], ""))}
        {metric_card("Highest function", complexity["max_complexity"], "worst case", RANK_TONE.get(complexity["rating"], ""))}
        {metric_card("Rating", complexity["rating"], "A best · F worst", RANK_TONE.get(complexity["rating"], ""))}
        {metric_card("Maintainability index", "N/A" if mi is None else mi, "Python only" if mi is None else complexity["mi_label"], "good" if mi is not None else "")}
        </div>"""
    )
    if complexity.get("details"):
        st.markdown("**Breakdown by function**")
        st.dataframe(pd.DataFrame(complexity["details"]).rename(
            columns={"name": "Function", "line": "Line", "complexity": "Complexity", "rank": "Rank"}), hide_index=True)
    if complexity.get("lines"):
        st.markdown("**Size**")
        st.dataframe(pd.DataFrame([complexity["lines"]]), hide_index=True)
    if result.get("complexity_notes"):
        st.markdown("**AI notes**")
        st.write(result["complexity_notes"])
    with st.expander("What do the ranks mean?"):
        st.markdown("Cyclomatic complexity counts the independent paths through a function: **A** 1-5 simple · **B** 6-10 · "
                    "**C** 11-20 · **D** 21-30 · **E** 31-40 · **F** 41+. Higher means harder to test and maintain.")


def render_score(result):
    score = result.get("overall_score", 0)
    details = result.get("score_details") or {}
    label, tone = score_band(score)
    c1, c2 = st.columns([1, 2])
    with c1:
        html_block(score_ring(score, 170))
    with c2:
        st.markdown(f"### Code health: **{score:g}/10** · {label}")
        st.progress(min(max(score / 10, 0.0), 1.0))
        {"green": st.success, "orange": st.warning, "red": st.error}[tone](
            {"green": "This code is in good shape.", "orange": "Decent, but there is room to improve.",
             "red": "This code needs significant work."}[tone])
    if details:
        st.markdown("**How the score is calculated**")
        rows = [{"Item": "Starting score", "Points": 10.0}] + [
            {"Item": p["label"].capitalize(), "Points": -p["points"]} for p in details.get("penalties", [])
        ] + [{"Item": "Rule-based score", "Points": details["rule_score"]}]
        if details.get("ai_score") is not None:
            rows += [{"Item": "AI opinion", "Points": details["ai_score"]},
                     {"Item": "Final = 60% rules + 40% AI", "Points": details["score"]}]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.caption("Rule-based penalties are deterministic, so the same code always loses the same points. "
                   "The AI opinion only adjusts 40% of the result.")


def render_diff(result):
    improved = result.get("improved_code", "")
    original = result.get("reviewed_code", "")
    language = result.get("language", "Python")
    if not improved:
        st.info("No improved version yet. Turn on AI review in the sidebar and analyze again.")
        return
    if result.get("improved_code_valid") is False:
        st.warning("Automatic checks found problems in the improved code. Review it before using it:\n\n"
                   + "\n".join(f"- {i}" for i in result.get("improved_code_issues", [])[:5]))
    else:
        st.success("The improved code passed the syntax and static checks.")
    tab_side, tab_diff = st.tabs(["Side by side", "Changes only"])
    with tab_side:
        left, right = st.columns(2)
        with left:
            st.markdown("**Original**")
            st.code(original, language=language.lower().replace("c++", "cpp"), line_numbers=True)
        with right:
            st.markdown("**AI-improved**")
            st.code(improved, language=language.lower().replace("c++", "cpp"), line_numbers=True)
    with tab_diff:
        diff = unified_diff(original, improved)
        st.code(diff or "No differences.", language="diff")
    ext = LANGUAGE_CONFIG.get(language, {"ext": ".txt"})["ext"]
    st.download_button("Download improved code", improved, file_name=f"improved{ext}")


def render_history():
    if not ss.history:
        st.info("Your reviews will appear here. Run an analysis to create the first entry.")
        return
    if len(ss.history) > 1:
        st.markdown("**Score trend** (oldest to newest)")
        st.line_chart(pd.DataFrame({"Score": [e["score"] for e in reversed(ss.history)]}))
    table = pd.DataFrame([
        {"Time": e["time"], "Language": e["language"], "Score": e["score"], "Critical": e["critical"],
         "Warnings": e["warning"], "Info": e["info"]} for e in ss.history
    ])
    st.dataframe(table, hide_index=True)
    labels = {e["id"]: f"{e['time']} · {e['language']} · {e['score']:g}/10" for e in ss.history}
    picked = st.selectbox("Reopen an earlier review", list(labels), format_func=labels.get)
    c1, c2, _ = st.columns([2, 2, 6])
    c1.button("Open review", on_click=open_history_entry, args=(picked,))
    if c2.button("Clear history"):
        ss.history = clear_history()
        st.rerun()


# ------------------------------------------------------------------ results
result, complexity = ss.result, ss.complexity
st.markdown("---")
if result and result.get("error"):
    st.error(result.get("summary") or "Something went wrong during the review.")
elif result:
    reviewed_language = result.get("language", language)
    reviewed_code = result.get("reviewed_code", code_input)
    stem = file_stem(reviewed_language)
    st.subheader("Review results")
    d1, d2, d3, _ = st.columns([2, 2, 2, 4])
    d1.download_button("Report (.md)", build_markdown(result, complexity, reviewed_code, reviewed_language),
                       file_name=f"{stem}.md", mime="text/markdown")
    d2.download_button("Report (.html)", build_html(result, complexity, reviewed_code, reviewed_language),
                       file_name=f"{stem}.html", mime="text/html")
    d3.download_button("Data (.json)", build_json(result, complexity, reviewed_code, reviewed_language),
                       file_name=f"{stem}.json", mime="application/json")
    tabs = st.tabs(["Overview", "Issues", "Improvements", "Complexity", "Score", "Before / After", "History"])
    with tabs[0]:
        render_overview(result, complexity)
    with tabs[1]:
        render_issues(result)
    with tabs[2]:
        render_improvements(result)
    with tabs[3]:
        render_complexity(result, complexity)
    with tabs[4]:
        render_score(result)
    with tabs[5]:
        render_diff(result)
    with tabs[6]:
        render_history()
else:
    st.info("Load a test case from the sidebar or paste your own code, then click **Analyze code**.")
    if ss.history:
        with st.expander(f"Review history ({len(ss.history)})"):
            render_history()
