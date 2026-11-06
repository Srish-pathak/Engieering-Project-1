import os
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="Tech Spec Analyser", page_icon="🪐", layout="wide")

from complexity import analyze_complexity
from github_fetcher import GitHubFetchError, fetch_public_repository
from report import build_json_report, build_markdown_report, build_repo_markdown
from reviewer import candidate_keys, detect_provider, has_deepseek_key, probe_deepseek_connectivity, review_code, review_repo_files
from theme import (
    banner, finding_card, hero, inject_css, rank_badge, score_ring, stat_row, tip_card,
)
from utils import LANGUAGE_CONFIG, score_label

try:
    from streamlit_ace import st_ace
    HAS_ACE = True
except ImportError:
    HAS_ACE = False

SAMPLES = {
    "Python": (
        "import os, sys\n\n"
        "def total(items, discount=[]):\n"
        "    try:\n"
        "        return sum(items) - sum(discount)\n"
        "    except:\n"
        "        pass\n\n"
        "def run(cmd):\n"
        "    eval(cmd)\n\n"
        "api_key = \"sk_live_1234567890abcdef\"\n"
        "print(total([1, 2, 3], 4, 5))\n"
    ),
    "C++": "#include <cstring>\nint add(int a, int b) {\n    char buf[8];\n    strcpy(buf, \"too long for this buffer\");\n    return a+b;\n}\n",
    "Java": "public class Demo {\n    int add(int a, int b) {\n        try { return a / b; }\n        catch (Exception e) { return 0; }\n    }\n}\n",
    "JavaScript": "var count = 0;\nfunction add(a, b) {\n    if (a == b) console.log('same');\n    return a + b;\n}\ndocument.body.innerHTML = location.hash;\n",
    "JSX": "function Greeting({ name }) {\n    return <h1 dangerouslySetInnerHTML={{__html: name}} />;\n}\n",
    "TypeScript": "function add(a: number, b: number): number {\n    return a + b;\n}\n",
    "TSX": "function Greeting({ name }: { name: string }) {\n    return <h1>Hello, {name}</h1>;\n}\n",
    "HTML": "<main>\n    <h1>Hello</h1>\n</main>\n",
    "CSS": "main {\n    color: navy;\n}\n",
    "SCSS": "$primary: navy;\n\nmain {\n    color: $primary;\n}\n",
}
EXT_TO_LANGUAGE = {cfg["ext"]: name for name, cfg in LANGUAGE_CONFIG.items()}
EXT_TO_LANGUAGE.update({".cc": "C++", ".cxx": "C++", ".hpp": "C++", ".h": "C++"})

DEFAULT_STATE = {
    "review_result": None,
    "complexity_result": None,
    "reviewed_code": "",
    "reviewed_language": "Python",
    "repository_result": None,
    "code_text": SAMPLES["Python"],
    "editor_version": 0,
    "language": "Python",
    "history": [],
    "api_key": "",
}
for key, value in DEFAULT_STATE.items():
    st.session_state.setdefault(key, value)

inject_css()


# ---------- callbacks (run before the script reruns, so widget state may be set) ----------
def load_sample() -> None:
    st.session_state.code_text = SAMPLES[st.session_state.language]
    st.session_state.editor_version += 1


def handle_upload() -> None:
    uploaded = st.session_state.get("uploaded_file")
    if uploaded is None:
        return
    extension = os.path.splitext(uploaded.name)[1].lower()
    language = EXT_TO_LANGUAGE.get(extension)
    try:
        text = uploaded.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        st.session_state.upload_error = "That file is not valid UTF-8 text."
        return
    st.session_state.upload_error = None
    st.session_state.code_text = text
    if language:
        st.session_state.language = language
    st.session_state.editor_version += 1


def clear_results() -> None:
    st.session_state.review_result = None
    st.session_state.complexity_result = None


# ---------- sidebar: just the key ----------
with st.sidebar:
    st.markdown("## 🔑 AI key")
    st.text_input(
        "AI API key", type="password", key="api_key", placeholder="DeepSeek sk-…  ·  Gemini AIza…  ·  Groq gsk_…",
        label_visibility="collapsed", help="Kept only in this browser session. Never saved.",
    )
    api_key = st.session_state.api_key.strip() or None
    if has_deepseek_key(api_key):
        providers = []
        for key in candidate_keys(api_key):
            name = detect_provider(key)
            if name not in providers:
                providers.append(name)
        st.success("AI review is on ({})".format(" → ".join(providers)))
        if len(providers) > 1:
            st.caption("If the first provider fails, the next one is used automatically.")
        if st.button("Test connection", use_container_width=True):
            probe = probe_deepseek_connectivity(api_key)
            if probe["connected"]:
                st.success("Connected to {} ({})".format(probe["provider"], probe["model"]))
            else:
                st.error(probe["error"])
    else:
        st.info("No key yet. You still get offline checks. Paste a key to turn on AI review.")
    with st.expander("🆓 Get a free key (no card)"):
        st.markdown(
            "**Google Gemini** (recommended)  \n"
            "[aistudio.google.com/apikey](https://aistudio.google.com/apikey) · key starts with `AIza`\n\n"
            "**Groq** (fast)  \n"
            "[console.groq.com/keys](https://console.groq.com/keys) · key starts with `gsk_`\n\n"
            "**DeepSeek** needs paid credit.\n\n"
            "On Streamlit Cloud you can also add `GEMINI_API_KEY` under *Settings → Secrets* "
            "so visitors don't need their own key."
        )

hero("TECH SPEC ANALYSER", "Paste code, get bugs, fixes and a score")

SEVERITY_ORDER = {"critical": 0, "high": 1, "warning": 2, "medium": 3, "low": 4, "info": 5}


def sort_findings(items):
    return sorted(items, key=lambda b: SEVERITY_ORDER.get(str(b.get("severity", "info")).lower(), 5))


tab_scan, tab_repo = st.tabs(["Check my code", "Check a GitHub repo"])


# ====================================================================== scanner
with tab_scan:
    pick_col, sample_col, _ = st.columns([1.2, 1.2, 3])
    language = pick_col.selectbox("Language", list(LANGUAGE_CONFIG.keys()), key="language", label_visibility="collapsed")
    sample_col.button("Load sample", on_click=load_sample, use_container_width=True)

    if HAS_ACE:
        code_input = st_ace(
            value=st.session_state.code_text,
            language=LANGUAGE_CONFIG[language]["ace_mode"],
            theme="tomorrow_night",
            font_size=14,
            height=300,
            key="editor_{}_{}".format(language, st.session_state.editor_version),
        )
    else:
        code_input = st.text_area(
            "Source code", value=st.session_state.code_text, height=300,
            key="textarea_{}".format(st.session_state.editor_version), label_visibility="collapsed",
        )
    if code_input is not None:
        st.session_state.code_text = code_input

    with st.expander("Or upload a file"):
        st.file_uploader(
            "Upload a source file", type=[e.lstrip(".") for e in EXT_TO_LANGUAGE],
            key="uploaded_file", on_change=handle_upload, label_visibility="collapsed",
        )
        if st.session_state.get("upload_error"):
            st.error(st.session_state.upload_error)

    run_clicked = st.button("Review My Code", type="primary")

    if run_clicked:
        source = st.session_state.code_text
        if not source or not source.strip():
            st.warning("Add some code first.")
        else:
            with st.spinner("Reviewing your code..."):
                result = review_code(source, language, "<input>", api_key)
                st.session_state.review_result = result
                st.session_state.reviewed_code = source
                st.session_state.reviewed_language = language
                st.session_state.complexity_result = (
                    analyze_complexity(source, language) if LANGUAGE_CONFIG[language]["supports_radon"] else None
                )
            st.session_state.history.append({
                "language": language,
                "findings": len(result.get("bugs", [])),
                "score": result.get("overall_score") if result.get("analysis_status", {}).get("ai") == "completed" else None,
                "time": datetime.now().strftime("%H:%M:%S"),
                "result": result,
                "complexity": st.session_state.complexity_result,
                "code": source,
            })

    result = st.session_state.review_result
    complexity = st.session_state.complexity_result

    if result:
        ai_status = result.get("analysis_status", {}).get("ai", "unknown")
        ai_ok = ai_status == "completed"
        bugs = sort_findings([b for b in result.get("bugs", []) if isinstance(b, dict)])
        improvements = [i for i in result.get("improvements", []) if isinstance(i, dict)]
        score = result.get("overall_score", 0)
        reviewed_language = st.session_state.reviewed_language

        st.markdown("---")
        if ai_ok and result.get("summary"):
            banner(result["summary"], "info")
            if result.get("ai_provider"):
                st.caption("Reviewed by {}".format(result["ai_provider"]))
        elif not ai_ok:
            banner("AI review is off ({}). Showing offline checks only. Add your DeepSeek key in the sidebar for the full review.".format(
                ai_status.replace("_", " ")), "warn")
        stat_row([
            ("Score", "{}/10".format(round(score, 1)) if ai_ok else "—", score_label(score) if ai_ok else "needs AI", "#34d399"),
            ("Issues", len(bugs), "found", "#fb7185"),
            ("Suggestions", len(improvements), "to improve", "#8b5cf6"),
        ])
        st.markdown("")

        t_issues, t_fixes, t_more = st.tabs(["Issues", "Fixes", "More"])

        with t_issues:
            if not bugs:
                banner("No issues found. ✅", "ok")
            for bug in bugs:
                st.markdown(finding_card(bug), unsafe_allow_html=True)

        with t_fixes:
            for tip in improvements:
                st.markdown(tip_card(tip), unsafe_allow_html=True)
            improved = result.get("improved_code", "")
            if improved:
                st.markdown("**Improved code**")
                st.code(improved, language=reviewed_language.lower())
            elif not improvements:
                banner("No fixes to suggest yet." if ai_ok else "Fixes need AI review. Add your key in the sidebar.", "info")

        with t_more:
            if complexity and not complexity.get("error") and complexity.get("details"):
                st.markdown("**Complexity**  ·  maintainability {}".format(complexity.get("maintainability_index", "N/A")))
                rows = "".join(
                    "<tr><td style='padding:.3rem .8rem'><code>{}</code></td><td style='padding:.3rem .8rem'>{}</td>"
                    "<td style='padding:.3rem .8rem'>{}</td></tr>".format(
                        d["name"].replace("<", "&lt;"), d["complexity"], rank_badge(d["rank"]))
                    for d in complexity["details"]
                )
                st.markdown("<div class='panel'><table style='width:100%'>{}</table></div>".format(rows), unsafe_allow_html=True)
            if ai_ok:
                st.markdown(score_ring(score, score_label(score)), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.download_button(
                "Download report (.md)",
                build_markdown_report(result, complexity, reviewed_language, st.session_state.reviewed_code),
                file_name="tech_spec_analyser_report.md", mime="text/markdown", use_container_width=True,
            )
            c2.download_button(
                "Download data (.json)", build_json_report(result, complexity),
                file_name="tech_spec_analyser_report.json", mime="application/json", use_container_width=True,
            )
            history = st.session_state.history
            if len(history) > 1:
                st.markdown("**Past reviews**")
                labels = ["{} · {} · {} issues".format(h["time"], h["language"], h["findings"]) for h in history]
                pick = st.selectbox("Past reviews", labels, index=len(labels) - 1, label_visibility="collapsed")
                if st.button("Open this review"):
                    entry = history[labels.index(pick)]
                    st.session_state.review_result = entry["result"]
                    st.session_state.complexity_result = entry["complexity"]
                    st.session_state.reviewed_code = entry["code"]
                    st.session_state.reviewed_language = entry["language"]
                    st.rerun()


# ====================================================================== repository
with tab_repo:
    url_col, btn_col = st.columns([4, 1.3])
    repository_url = url_col.text_input(
        "Public repository URL", placeholder="https://github.com/owner/repository", key="repository_url",
        label_visibility="collapsed",
    )
    analyze_clicked = btn_col.button("Analyze Repository", type="primary", use_container_width=True)
    st.caption("Public repos only, up to 30 files. Code is sent to DeepSeek when a key is set.")

    if analyze_clicked:
        if not repository_url.strip():
            st.warning("Enter a public GitHub repository URL first.")
        else:
            try:
                with st.spinner("Fetching files from GitHub..."):
                    repository_data = fetch_public_repository(repository_url)
                if not repository_data["files"]:
                    st.session_state.repository_result = None
                    st.warning("No supported source files were found in this repository.")
                else:
                    progress = st.progress(0.0, text="Starting...")

                    def update_progress(done, total, path):
                        progress.progress(done / total, text="Reviewed {}/{} files · {}".format(done, total, path))

                    review_data = review_repo_files(repository_data["files"], update_progress, api_key)
                    progress.empty()
                    st.session_state.repository_result = {"repository": repository_data, "review": review_data}
            except GitHubFetchError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error("Repository review could not be completed: {}".format(exc))

    repo_result = st.session_state.repository_result
    if repo_result:
        repo = repo_result["repository"]
        review = repo_result["review"]
        st.markdown("---")
        st.markdown("**[{}]({})** · `{}`".format(repo["full_name"], repo["html_url"], repo["branch"]))
        stat_row([
            ("Files reviewed", review["files_reviewed"], "of {} found".format(repo["source_files_detected"]), "#22d3ee"),
            ("Serious issues", review["critical_bugs"] + review["warnings"], "critical + warnings", "#fb7185"),
            ("Quality", "{}/10".format(review["overall_score"]) if review["overall_score"] is not None else "—",
             score_label(review["overall_score"]) if review["overall_score"] is not None else "needs AI", "#34d399"),
        ])
        st.markdown("")
        notes = []
        if repo.get("files_limited"):
            notes.append("Only the first 30 files were reviewed.")
        if review.get("failed_files"):
            notes.append("{} file(s) could not be reviewed.".format(review["failed_files"]))
        if review.get("ai_failed_files"):
            notes.append("AI review was unavailable for {} file(s); offline checks were used.".format(review["ai_failed_files"]))
        if repo.get("fetch_errors"):
            notes.append("{} file(s) could not be downloaded.".format(len(repo["fetch_errors"])))
        if notes:
            banner(" ".join(notes), "warn")

        all_bugs = []
        for file_result in review["file_results"]:
            all_bugs += [(file_result["path"], b) for b in file_result["review"].get("bugs", []) if isinstance(b, dict)]
        all_bugs.sort(key=lambda pb: SEVERITY_ORDER.get(str(pb[1].get("severity", "info")).lower(), 5))

        r_issues, r_files = st.tabs(["Issues", "Files"])
        with r_issues:
            if not all_bugs:
                banner("No issues found. ✅", "ok")
            for path, bug in all_bugs:
                st.markdown(finding_card(bug, path), unsafe_allow_html=True)
            st.download_button(
                "Download report (.md)", build_repo_markdown(repo, review),
                file_name="tech_spec_analyser_repo_report.md", mime="text/markdown",
            )
        with r_files:
            paths = [f["path"] for f in review["file_results"]]
            selected_path = st.selectbox("File", paths, label_visibility="collapsed")
            selected = next(f for f in review["file_results"] if f["path"] == selected_path)
            file_review = selected["review"]
            st.write(file_review.get("summary") or "No summary.")
            for bug in sort_findings([b for b in file_review.get("bugs", []) if isinstance(b, dict)]):
                st.markdown(finding_card(bug), unsafe_allow_html=True)
            for tip in [i for i in file_review.get("improvements", []) if isinstance(i, dict)]:
                st.markdown(tip_card(tip), unsafe_allow_html=True)
            with st.expander("Show source code"):
                st.code(selected["content"], language=selected["language"].lower())
            if file_review.get("improved_code"):
                with st.expander("Show improved code"):
                    st.code(file_review["improved_code"], language=selected["language"].lower())
