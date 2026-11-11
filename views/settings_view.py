"""
TechSpecAnalyser — Settings & Webhook Configuration View.
Manages API keys, model selection, webhook signatures, and deployment instructions.
"""
import os
import streamlit as st

from config import (
    APP_NAME,
    DB_PATH,
    DEFAULT_GEMINI_MODEL,
    WEBHOOK_SECRET,
    get_gemini_api_key,
    get_github_token,
    is_gemini_configured,
)
from core.gemini_client import GeminiClient
from database.repositories import get_recent_webhooks


def render_settings_view() -> None:
    """Renders the Settings & Integrations view."""
    st.markdown(
        """
        <div class="ts-header">
          <h1>Platform Settings & Webhook Config</h1>
          <p>Configure Google Gemini models, GitHub Personal Access Tokens, and webhook automation.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_api, tab_webhook, tab_system = st.tabs(["🔑 API & AI Models", "⚡ GitHub Webhooks", "⚙️ System & Privacy"])

    # 1. API & AI Models
    with tab_api:
        st.subheader("Google Gemini AI Configuration")

        current_key = get_gemini_api_key()
        api_key_input = st.text_input(
            "Google Gemini API Key",
            type="password",
            value=current_key,
            help="Get your API key at https://aistudio.google.com/app/apikey. Sidebar override takes priority.",
        )
        if api_key_input != current_key:
            st.session_state["custom_gemini_key"] = api_key_input
            os.environ["GEMINI_API_KEY"] = api_key_input

        model_options = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
        current_model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        selected_model = st.selectbox(
            "Default Gemini Model",
            model_options,
            index=model_options.index(current_model) if current_model in model_options else 0,
        )
        os.environ["GEMINI_MODEL"] = selected_model

        if st.button("🧪 Test Gemini API Connection"):
            try:
                client = GeminiClient(api_key=api_key_input, model_name=selected_model)
                res = client.get_client().models.generate_content(
                    model=selected_model,
                    contents="Reply with 'TechSpecAnalyser AI Engine OK'.",
                )
                st.success(f"Connection Successful! Model `{selected_model}` responded: {res.text.strip()}")
            except Exception as e:
                st.error(f"Gemini API connection failed: {e}")

        st.markdown("---")
        st.subheader("GitHub Authentication")
        current_gh_token = get_github_token()
        gh_token_input = st.text_input(
            "GitHub Personal Access Token (PAT)",
            type="password",
            value=current_gh_token,
            help="Allows access to private repositories and increases GitHub rate limit from 60 to 5,000 requests/hour.",
        )
        if gh_token_input != current_gh_token:
            st.session_state["custom_github_token"] = gh_token_input
            os.environ["GITHUB_TOKEN"] = gh_token_input

    # 2. GitHub Webhook Setup
    with tab_webhook:
        st.subheader("Automated GitHub Push Webhook Service")
        st.markdown(
            """
            When you push code to GitHub, GitHub automatically notifies the **TechSpecAnalyser Webhook Service**
            which fetches the changed files, runs offline static analysis, triggers Gemini review, and updates your dashboard.
            """
        )

        st.markdown("#### Webhook Endpoint URL:")
        st.code("http://<YOUR_DEPLOYED_DOMAIN_OR_NGROK>/webhooks/github", language="text")

        st.markdown("#### Configured Webhook Secret (HMAC-SHA256):")
        st.code(WEBHOOK_SECRET, language="text")

        st.markdown("#### Local Testing Instructions:")
        st.markdown(
            """
            1. **Start the Webhook Service:**
               ```bash
               uvicorn api:app --host 0.0.0.0 --port 8000
               ```
            2. **Expose with a Tunnel (e.g. ngrok or smee.io):**
               ```bash
               ngrok http 8000
               ```
            3. **In your GitHub Repository Settings:**
               - Go to **Settings** → **Webhooks** → **Add Webhook**
               - **Payload URL:** `https://<your-ngrok-id>.ngrok-free.app/webhooks/github`
               - **Content type:** `application/json`
               - **Secret:** Enter the configured secret above (`WEBHOOK_SECRET`)
               - **Which events:** Select **Just the push event**
               - Click **Add Webhook**.
            """
        )

        st.markdown("#### Recent Webhook Deliveries")
        recent_wh = get_recent_webhooks(limit=10)
        if recent_wh:
            st.dataframe(recent_wh, use_container_width=True)
        else:
            st.info("No webhook deliveries recorded yet.")

    # 3. System & Privacy
    with tab_system:
        st.subheader("Privacy & Security Guarantees")
        st.markdown(
            f"""
            - **Platform:** {APP_NAME}
            - **Database Path:** `{DB_PATH}`
            - **Local Execution:** All AST parsing, syntax validation, and McCabe complexity analysis run 100% locally on your machine.
            - **Secret Redaction:** Passwords, AWS keys, GitHub tokens, and JWTs are automatically masked before any external transmission.
            - **Offline Mode:** If Gemini AI review is disabled or unconfigured, zero source code leaves your local environment.
            """
        )
