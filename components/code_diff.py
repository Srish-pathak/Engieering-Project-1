"""
TechSpecAnalyser — Code Diff Renderer Component.
Displays side-by-side and unified diff comparisons with line numbers.
"""
from typing import Optional

import streamlit as st

from reports.export import unified_diff


def render_code_comparison(
    original_code: str,
    improved_code: str,
    language: str = "python",
    title_original: str = "Original Code",
    title_improved: str = "AI Optimized & Corrected Code",
) -> None:
    """Renders side-by-side code blocks and unified diff."""
    if not improved_code:
        st.info("No improved code version available.")
        return

    tab_side, tab_unified = st.tabs(["Side-by-Side Comparison", "Unified Diff View"])

    with tab_side:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**{title_original}**")
            st.code(original_code, language=language.lower())
        with col2:
            st.markdown(f"**{title_improved}**")
            st.code(improved_code, language=language.lower())

    with tab_unified:
        diff_text = unified_diff(original_code, improved_code)
        if diff_text:
            st.code(diff_text, language="diff")
        else:
            st.success("Original code and improved code are identical (no changes).")
