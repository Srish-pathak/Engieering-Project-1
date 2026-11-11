"""
TechSpecAnalyser — AI Developer Assistant View.
Interactive conversational agent grounded in repository facts, active findings,
and file references with persistent SQLite chat history.
"""
import streamlit as st

from assistant.codebase_assistant import CodebaseAssistant
from config import is_gemini_configured
from database.repositories import get_chat_history


def render_assistant_view() -> None:
    """Renders the AI Developer Assistant chat interface."""
    st.markdown(
        """
        <div class="ts-header">
          <h1>AI Developer Assistant</h1>
          <p>Chat with your codebase. Grounded in deterministic repository facts, AST findings, and source files.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not is_gemini_configured():
        st.warning(
            "⚠️ Google Gemini API key is not configured. Assistant is operating in offline mode. "
            "Enter your key in the sidebar or `.env` file to chat with your codebase."
        )

    active_result = st.session_state.get("active_review_result")
    repo_name = (active_result.get("repo_full_name") or active_result.get("project_name", "General")) if active_result else "General"

    st.markdown(f"**Active Codebase Context:** `{repo_name}`")

    # If user arrived from clicking "Ask Assistant about this finding"
    pending_finding = st.session_state.get("assistant_finding_context")
    if pending_finding:
        st.info(f"📍 Context attached: **{pending_finding.get('title')}** ({pending_finding.get('file')}:{pending_finding.get('line')})")
        if st.button("Clear Finding Context"):
            st.session_state["assistant_finding_context"] = None
            st.rerun()

    # Quick prompt buttons
    st.markdown("**Suggested Questions:**")
    q_cols = st.columns(3)
    preset_query = None
    with q_cols[0]:
        if st.button("Explain this entire project architecture"):
            preset_query = "Explain this entire project architecture, its primary purpose, and data flow."
    with q_cols[1]:
        if st.button("Which files have the most critical bugs?"):
            preset_query = "Which files contain the most critical bugs and security weaknesses, and what should be fixed first?"
    with q_cols[2]:
        if st.button("How can I optimize this codebase?"):
            preset_query = "How can I optimize this codebase to reduce complexity and improve maintainability?"

    st.markdown("---")

    # Display past conversation history
    history = get_chat_history(repo_name, limit=20)
    for msg in history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    user_query = st.chat_input("Ask a question about this repository...") or preset_query
    if user_query:
        with st.chat_message("user"):
            st.write(user_query)

        assistant = CodebaseAssistant()
        with st.chat_message("assistant"):
            with st.spinner("Analyzing codebase context and reasoning..."):
                answer = assistant.ask(
                    query=user_query,
                    repo_data=active_result,
                    selected_finding=pending_finding,
                )
                st.write(answer)
        st.rerun()
