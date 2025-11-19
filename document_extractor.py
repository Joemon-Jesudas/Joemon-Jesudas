# ui/display_manager.py
import streamlit as st
from typing import Any, Dict

def get_safe_usage_value(usage: Dict[str, int], key: str) -> int:
    try:
        return int(usage.get(key, 0))
    except Exception:
        return 0

class DisplayManager:
    """All UI rendering logic for displaying extraction results."""

    @staticmethod
    def show_file_info(uploaded_file) -> None:
        size_mb = uploaded_file.size / (1024 * 1024)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("File Name", uploaded_file.name)
        with col2:
            st.metric("File Size", f"{size_mb:.2f} MB")
        if size_mb > 50:
            st.warning("⚠️ File size exceeds 50 MB. Processing may take longer.")

    @staticmethod
    def show_processing_stats(extraction_time: float, analysis_time: float, page_count: int, processed_time: str, usage_stats: Dict[str, int] | None = None) -> None:
        """
        Show processing stats in the sidebar.
        usage_stats: dict with keys 'prompt_tokens', 'completion_tokens', 'total_tokens'
        """
        st.sidebar.subheader("📊 Processing Statistics")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Extraction Time", f"{extraction_time:.2f}s")
        with col2:
            st.metric("Analysis Time", f"{analysis_time:.2f}s")

        st.sidebar.metric("Pages Processed", page_count)
        st.sidebar.caption(f"Processed: {processed_time}")

        # Token usage: be defensive if usage_stats is None or malformed
        st.sidebar.subheader("🧮 Token Usage")
        if usage_stats is None:
            st.sidebar.write("No token usage data available.")
            st.sidebar.metric("Input Tokens", 0)
            st.sidebar.metric("Output Tokens", 0)
            st.sidebar.metric("Total Tokens", 0)
            return

        prompt_tokens = get_safe_usage_value(usage_stats, "prompt_tokens")
        completion_tokens = get_safe_usage_value(usage_stats, "completion_tokens")
        total_tokens = get_safe_usage_value(usage_stats, "total_tokens")

        st.sidebar.metric("Input Tokens", prompt_tokens)
        st.sidebar.metric("Output Tokens", completion_tokens)
        st.sidebar.metric("Total Tokens", total_tokens)

    @staticmethod
    def show_results(result_json: Dict[str, Any]) -> None:
        st.divider()
        st.subheader("📊 Extraction Results")
        # ... (rest of your existing show_results implementation)
        with st.expander("📋 View Raw JSON", expanded=False):
            st.json(result_json)
