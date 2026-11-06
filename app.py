from datetime import datetime

import streamlit as st

st.set_page_config(page_title="AI Code Reviewer", page_icon="🔍", layout="wide")

from github_fetcher import MAX_FILES, GitHubFetchError, fetch_public_repository
from report import build_json_report, build_markdown_report, build_repo_markdown
from reviewer import (
    DEFAULT_MODEL, has_key, probe_connection, resolve_model, review_code, review_repo_files,
)
from utils import (
    LANGUAGE_CONFIG, format_bug_entry, format_improvement_entry, score_color, score_label, sort_findings,
)

try:
    from streamlit_ace import st_ace
    HAS_ACE = True
except ImportError:
    HAS_ACE = False

SAMPLES = {
    "Python": (
        "import os, sys\n\n"
        "def total(items, discount=[]):\n"
        "    try:\n        return sum(items) - sum(discount)\n    except:\n        pass\n\n"
        "def run(cmd):\n    eval(cmd)\n\n"
        'api_key = "sk_live_1234567890abcdef"\n'
        "print(total([1, 2, 3], 4, 5))\n"
    ),
    "C++": '#include <cstring>\nint add(int a, int b) {\n    char buf[8];\n    strcpy(buf, "too long for this buffer");\n    return a+b;\n}\n',
    "Java": "public class Demo {\n    int add(int a, int b) {\n        try { return a / b; }\n        catch (Exception e) { return 0; }\n    }\n}\n",
    "JavaScript": "var count = 0;\nfunction add(a, b) {\n    if (a == b) console.log('same');\n    return a + b;\n}\ndocument.body.innerHTML = location.hash;\n",
    "JSX": "function Greeting({ name }) {\n    return <h1 dangerouslySetInnerHTML={{__html: name}} />;\n}\n",
    "TypeScript": "function add(a: number, b: number): number {\n    return a + b;\n}\n",
    "TSX": "function Greeting({ name }: { name: string }) {\n    return <h1>Hello, {name}</h1>;\n}\n",
    "HTML": "<main>\n    <h1>Hello</h1>\n</main>\n",
    "CSS": "main {\n    color: navy;\n}\n",
    "SCSS": "$primary: navy;\n\nmain {\n    color: $primary;\n}\n",
}

for key, value in {"review_result": None, "reviewed_code": "", "reviewed_language": "Python",
                   "repo_result": None, "history": []}.items():
    st.session_state.setdefault(key, value)


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    st.text_input(
        "Gemini API key", type="password", key="api_key", placeholder="AIza...",
        help="Free at aistudio.google.com/apikey. Kept only in this browser session.",
    )
    st.text_input("Model", value=resolve_model(None), key="model_name",
                  help="Default {}. Change it if Google renames or retires a model.".format(DEFAULT_MODEL))
    api_key = st.session_state.api_key.strip() or None
    model = st.session_state.model_name.strip() or None

    if has_key(api_key):
        st.success("AI review is on")
        if st.button("Test connection", use_container_width=True):
            probe = probe_connection(api_key, model)
            if probe["connected"]:
                st.success("Connected ({})".format(probe["model"]))
            else:
                st.error(probe["error"])
    else:
        st.info("No key yet. Offline checks still work. Get a free key at aistudio.google.com/apikey.")
    st.caption("Source code is sent to Google Gemini when AI review is on. Free-tier prompts may be used by Google to improve its products.")

st.title("🔍 AI Code Reviewer")
st.caption("Paste code or analyse a public GitHub repository: bugs, improvements, complexity and a score.")

tab_code, tab_repo = st.tabs(["📝 Check my code", "🐙 Analyse a GitHub repo"])


# ------------------------------------------------------------------ shared renderer
def render_review(result: dict, code: str, language: str, key: str) -> None:
    """Show one file's review. ``key`` keeps widget ids unique across files."""
    status = result.get("analysis_status", {}).get("ai", "unknown")
    if status != "completed":
        label = {"skipped": "AI review was skipped. Showing offline checks only."}.get(
            status, result.get("ai_error") or "AI review did not run. Showing offline checks only.")
        st.warning(label)
    elif result.get("summary"):
        st.info(result["summary"])

    bugs = sort_findings(result.get("bugs", []))
    improvements = [i for i in result.get("improvements", []) if isinstance(i, dict)]
    score = result.get("overall_score")
    c1, c2, c3 = st.columns(3)
    c1.metric("Score", "{}/10".format(round(score, 1)) if status == "completed" and score is not None else "—")
    c2.metric("Issues", len(bugs))
    c3.metric("Suggestions", len(improvements))

    t_bugs, t_fix, t_cx, t_diff = st.tabs(["🐛 Issues", "💡 Improvements", "⚙️ Complexity", "🔀 Before / After"])
    with t_bugs:
        if not bugs:
            st.success("No issues found. ✅")
        for bug in bugs:
            st.markdown(format_bug_entry(bug))
    with t_fix:
        if not improvements:
            st.info("No suggestions yet." if status == "completed" else "Suggestions need the AI review.")
        for item in improvements:
            st.markdown(format_improvement_entry(item))
    with t_cx:
        cx = result.get("complexity")
        if cx:
            m1, m2, m3 = st.columns(3)
            m1.metric("Method", cx["method"].title())
            m2.metric("Avg. complexity", cx["average_complexity"])
            m3.metric("Rating", cx["rating"])
            if cx.get("maintainability_index") is not None:
                st.metric("Maintainability index", cx["maintainability_index"])
            if cx.get("details"):
                st.table(cx["details"])
            if cx.get("error"):
                st.warning(cx["error"])
        if result.get("complexity_notes"):
            st.caption(result["complexity_notes"])
        if status == "completed":
            st.markdown("**Health:** {}/10 — {}".format(round(score, 1), score_label(score)))
            st.progress(min(max(score / 10, 0.0), 1.0))
            {"green": st.success, "orange": st.warning, "red": st.error}[score_color(score)](
                {"green": "This code is in great shape!", "orange": "Decent, but there is room to improve.",
                 "red": "This code needs significant work."}[score_color(score)])
    with t_diff:
        improved = result.get("improved_code", "")
        if improved:
            left, right = st.columns(2)
            left.markdown("**Original**")
            left.code(code, language=language.lower())
            right.markdown("**AI-improved**")
            right.code(improved, language=language.lower())
        else:
            st.info("No improved version was returned.")


# ------------------------------------------------------------------ single code tab
with tab_code:
    top_left, top_right, _ = st.columns([1.5, 1.2, 4])
    language = top_left.selectbox("Language", list(LANGUAGE_CONFIG.keys()), label_visibility="collapsed")
    use_sample = top_right.button("Load sample", use_container_width=True)
    st.session_state.setdefault("editor_nonce", 0)
    if use_sample:
        st.session_state.editor_nonce += 1

    editor_key = "editor_{}_{}".format(language, st.session_state.editor_nonce)
    if HAS_ACE:
        code_input = st_ace(value=SAMPLES[language], language=LANGUAGE_CONFIG[language]["ace_mode"],
                            theme="tomorrow_night", font_size=14, height=300, key=editor_key)
    else:
        code_input = st.text_area("Source code", value=SAMPLES[language], height=300, key=editor_key,
                                  label_visibility="collapsed")

    if st.button("Review My Code", type="primary"):
        if not code_input or not code_input.strip():
            st.warning("Please paste some code first.")
        else:
            with st.spinner("Reviewing your code..."):
                result = review_code(code_input, language, "<input>", api_key, model)
            st.session_state.review_result = result
            st.session_state.reviewed_code = code_input
            st.session_state.reviewed_language = language
            st.session_state.history.append({
                "time": datetime.now().strftime("%H:%M:%S"), "language": language,
                "issues": len(result.get("bugs", [])), "result": result, "code": code_input,
            })

    result = st.session_state.review_result
    if result:
        st.markdown("---")
        reviewed_language = st.session_state.reviewed_language
        render_review(result, st.session_state.reviewed_code, reviewed_language, "single")
        d1, d2 = st.columns(2)
        d1.download_button("Download report (.md)",
                           build_markdown_report(result, reviewed_language, st.session_state.reviewed_code),
                           file_name="code_review.md", mime="text/markdown", use_container_width=True)
        d2.download_button("Download data (.json)", build_json_report(result),
                           file_name="code_review.json", mime="application/json", use_container_width=True)

        history = st.session_state.history
        if len(history) > 1:
            with st.expander("Past reviews this session"):
                labels = ["{} · {} · {} issues".format(h["time"], h["language"], h["issues"]) for h in history]
                pick = st.selectbox("Past reviews", labels, index=len(labels) - 1, label_visibility="collapsed")
                if st.button("Open this review"):
                    entry = history[labels.index(pick)]
                    st.session_state.review_result = entry["result"]
                    st.session_state.reviewed_code = entry["code"]
                    st.session_state.reviewed_language = entry["language"]
                    st.rerun()


# ------------------------------------------------------------------ GitHub tab
with tab_repo:
    url_col, btn_col = st.columns([4, 1.4])
    repository_url = url_col.text_input(
        "Public repository URL", placeholder="https://github.com/owner/repository",
        key="repository_url", label_visibility="collapsed")
    analyze_clicked = btn_col.button("Analyse repository", type="primary", use_container_width=True)

    opt1, opt2 = st.columns(2)
    use_ai = opt1.checkbox("Use Gemini AI for each file", value=has_key(api_key),
                           help="Off = fast offline checks only (no API quota used).")
    max_files = opt2.slider("Max files to review", 1, MAX_FILES, 8,
                            help="Free Gemini keys allow only a few requests per minute, so start small.")
    st.caption("Public repos only. Python files are reviewed first. GitHub allows 60 unauthenticated requests/hour, "
               "and each file costs one request.")

    if analyze_clicked:
        if not repository_url.strip():
            st.warning("Enter a public GitHub repository URL first.")
        else:
            try:
                with st.spinner("Fetching files from GitHub..."):
                    repo_data = fetch_public_repository(repository_url, max_files)
                if not repo_data["files"]:
                    st.session_state.repo_result = None
                    st.warning("No supported source files were found in this repository.")
                else:
                    progress = st.progress(0.0, text="Starting...")

                    def on_progress(done, total, path):
                        progress.progress(done / total, text="Reviewed {}/{} · {}".format(done, total, path))

                    review_data = review_repo_files(
                        repo_data["files"], on_progress, api_key, model, use_ai=use_ai and has_key(api_key))
                    progress.empty()
                    st.session_state.repo_result = {"repository": repo_data, "review": review_data}
            except GitHubFetchError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error("Repository review could not be completed: {}".format(exc))

    repo_result = st.session_state.repo_result
    if repo_result:
        repo, review = repo_result["repository"], repo_result["review"]
        counts = review["severity_counts"]
        st.markdown("---")
        st.markdown("**[{}]({})** · branch `{}`".format(repo["full_name"], repo["html_url"], repo["branch"]))
        if repo["description"]:
            st.caption(repo["description"])

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Files reviewed", "{} / {}".format(review["files_reviewed"], repo["source_files_detected"]))
        m2.metric("Critical + High", counts["critical"] + counts["high"])
        m3.metric("Medium + Low", counts["medium"] + counts["low"])
        score = review["overall_score"]
        m4.metric("Avg. AI score", "{}/10".format(score) if score is not None else "—")

        notes = []
        if repo["files_limited"]:
            notes.append("Only the first {} of {} source files were reviewed.".format(
                review["files_reviewed"], repo["source_files_detected"]))
        if repo["tree_truncated"]:
            notes.append("GitHub truncated the file list for this very large repo.")
        if repo["fetch_errors"]:
            notes.append("{} file(s) could not be downloaded.".format(len(repo["fetch_errors"])))
        if review["ai_stopped_reason"]:
            notes.append("AI stopped early: {} Remaining files used offline checks.".format(review["ai_stopped_reason"]))
        elif review["ai_failed_files"]:
            notes.append("AI review failed for {} file(s).".format(review["ai_failed_files"]))
        for note in notes:
            st.warning(note)

        r_over, r_files = st.tabs(["Overview", "Files"])
        with r_over:
            rows = []
            for item in review["file_results"]:
                r = item["review"]
                bugs = [b for b in r.get("bugs", []) if isinstance(b, dict)]
                sc = r.get("overall_score")
                rows.append({
                    "File": item["path"], "Language": item["language"],
                    "Critical/High": sum(1 for b in bugs if str(b.get("severity", "")).lower() in {"critical", "high"}),
                    "Other": sum(1 for b in bugs if str(b.get("severity", "")).lower() not in {"critical", "high"}),
                    "AI score": round(sc, 1) if r.get("analysis_status", {}).get("ai") == "completed" and sc is not None else None,
                })
            rows.sort(key=lambda row: (-row["Critical/High"], -row["Other"]))
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.download_button("Download repository report (.md)", build_repo_markdown(repo, review),
                               file_name="repo_report.md", mime="text/markdown")
        with r_files:
            for item in review["file_results"]:
                r = item["review"]
                issues = len([b for b in r.get("bugs", []) if isinstance(b, dict)])
                with st.expander("{} · {} issue(s)".format(item["path"], issues)):
                    render_review(r, item["content"], item["language"], item["path"])
