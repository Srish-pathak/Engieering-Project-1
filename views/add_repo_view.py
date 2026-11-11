"""
TechSpecAnalyser — Add & Connect GitHub Repository View.
Enables connecting public or private GitHub repositories, branch selection,
file filtering safeguards, and triggering automated repository-wide reviews.
"""
import streamlit as st

from config import DEFAULT_MAX_FILE_BYTES, DEFAULT_MAX_REPO_FILES, is_gemini_configured
from core.review_orchestrator import ReviewOrchestrator
from integrations.github_client import GitHubClient
from integrations.github_fetcher import GitHubFetcher


def render_add_repo_view() -> None:
    """Renders the Add Repository workflow."""
    st.markdown(
        """
        <div class="ts-header">
          <h1>Connect GitHub Repository</h1>
          <p>Analyze public or private GitHub repositories with automated static intelligence and Google Gemini reasoning.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_input, col_info = st.columns([1.5, 1.0])

    with col_input:
        repo_url = st.text_input(
            "GitHub Repository URL or Slug",
            value=st.session_state.get("last_repo_url", "https://github.com/octocat/Hello-World"),
            placeholder="e.g. https://github.com/facebook/react or owner/repo",
            help="Public repositories work immediately. For private repositories, enter a Personal Access Token below or in the sidebar.",
        )

        with st.expander("🔐 Authentication & Advanced Filtering Settings", expanded=False):
            token_input = st.text_input(
                "GitHub Personal Access Token (PAT)",
                type="password",
                value=st.session_state.get("custom_github_token", ""),
                help="Only required for private repositories or to bypass GitHub's 60 req/hr unauthenticated rate limit.",
            )
            if token_input:
                st.session_state["custom_github_token"] = token_input

            max_files = st.slider("Maximum Files to Analyze", min_value=5, max_value=80, value=DEFAULT_MAX_REPO_FILES)
            max_kb = st.slider("Maximum File Size (KB)", min_value=50, max_value=500, value=int(DEFAULT_MAX_FILE_BYTES / 1024))

        # Check repository & fetch branches
        if st.button("🔍 Connect & Inspect Repository Structure", type="primary"):
            if not repo_url.strip():
                st.error("Please enter a valid GitHub repository URL or slug.")
                return

            try:
                client = GitHubClient(token=token_input)
                owner, repo = client.parse_repo_url(repo_url)
                with st.spinner(f"Connecting to {owner}/{repo}..."):
                    meta = client.get_repo(owner, repo)
                    branches = client.get_branches(owner, repo)
                    branch_names = [b["name"] for b in branches]
                    commits = client.get_commits(owner, repo, branch=meta.get("default_branch", "main"))

                st.session_state["active_repo_meta"] = meta
                st.session_state["active_repo_branches"] = branch_names
                st.session_state["active_repo_commits"] = commits
                st.session_state["last_repo_url"] = repo_url
                st.session_state["repo_owner"] = owner
                st.session_state["repo_name"] = repo
                st.success(f"Connected to **{meta.get('full_name')}** ({meta.get('stargazers_count', 0):,} ★)!")
            except Exception as e:
                st.error(f"Failed to connect to repository: {e}")

    with col_info:
        st.markdown(
            """
            <div class="ts-metric-card">
              <div class="ts-metric-label">Built-in Safeguards</div>
              <ul style="color:var(--muted); font-size:0.88rem; padding-left:1.2rem; margin-top:0.5rem;">
                <li>Max 30 files analyzed by default (configurable)</li>
                <li>Max 200 KB per individual file</li>
                <li>Excludes <code>node_modules</code>, <code>.venv</code>, binaries, builds</li>
                <li>Fault-isolated: one bad file never halts review</li>
                <li>Never stores or transmits unredacted credentials</li>
              </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # If repo metadata is loaded in session, show branch selector and analysis launcher
    if "active_repo_meta" in st.session_state:
        meta = st.session_state["active_repo_meta"]
        branches = st.session_state.get("active_repo_branches", ["main"])
        owner = st.session_state["repo_owner"]
        repo = st.session_state["repo_name"]

        st.markdown("---")
        st.subheader("Repository Configuration & Target Branch")

        col_b, col_c = st.columns([1, 1])
        with col_b:
            selected_branch = st.selectbox(
                "Select Branch",
                options=branches,
                index=branches.index(meta.get("default_branch", "main")) if meta.get("default_branch") in branches else 0,
            )

        with col_c:
            use_ai = st.checkbox(
                "Enable Google Gemini AI Review",
                value=is_gemini_configured(),
                help="Combines deterministic static findings with Gemini explanations and architecture insights.",
            )

        if st.button("🚀 Start Full Repository Intelligence & Review", type="primary"):
            progress_bar = st.progress(0.0)
            status_text = st.empty()

            def _progress(msg: str, pct: float):
                progress_bar.progress(pct)
                status_text.info(msg)

            try:
                fetcher = GitHubFetcher(
                    client=GitHubClient(token=st.session_state.get("custom_github_token")),
                    max_files=max_files,
                    max_file_bytes=max_kb * 1024,
                )
                files, fetch_meta = fetcher.fetch_repository_files(owner, repo, branch=selected_branch, progress_cb=_progress)

                orchestrator = ReviewOrchestrator()
                repo_result = orchestrator.review_repository_files(
                    files=files,
                    project_name=meta.get("full_name", f"{owner}/{repo}"),
                    repo_url=meta.get("html_url", repo_url),
                    branch=selected_branch,
                    commit_sha=fetch_meta.get("head_commit_sha", ""),
                    use_ai=use_ai,
                    progress_cb=_progress,
                )

                st.session_state["active_review_result"] = repo_result
                status_text.success("Analysis complete! Review report is now ready.")
                st.session_state["active_nav"] = "🔍 Code Review"
                st.rerun()

            except Exception as e:
                status_text.error(f"Repository review failed: {e}")
