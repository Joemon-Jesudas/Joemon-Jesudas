import streamlit as st
from typing import Any, Dict
from utils.validators import get_status_style

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
    def show_processing_stats(extraction_time: float, analysis_time: float, page_count: int, processed_time: str) -> None:
        st.sidebar.subheader("📊 Processing Statistics")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Extraction Time", f"{extraction_time:.2f}s")
        with col2:
            st.metric("Analysis Time", f"{analysis_time:.2f}s")
        st.sidebar.metric("Pages Processed", page_count)
        st.sidebar.caption(f"Processed: {processed_time}")

    @staticmethod
    def show_results(result_json: Dict[str, Any]) -> None:
        st.divider()
        st.subheader("📊 Extraction Results")

        # Template Classification
        with st.expander("📋 Template Classification", expanded=True):
            template = result_json.get("template_classification", {})
            st.write(f"**Type:** {template.get('type', 'N/A')}")
            keywords = template.get("keywords_found", [])
            st.write(f"**Keywords:** {', '.join(keywords) if keywords else 'None'}")
            st.write(f"**Confidence:** {template.get('confidence', 'N/A')}")

        # Party Information
        with st.expander("🏢 Party Information", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                allianz = result_json.get("allianz_details", {})
                st.write("**Allianz Details**")
                st.write(f"Name: {allianz.get('name', 'N/A')}")
                st.write(f"Address: {allianz.get('address', 'N/A')}")
                status = allianz.get("validation_status", "N/A")
                st.markdown(f"Status: <span class='{get_status_style(status)}'>{status}</span>", unsafe_allow_html=True)
            with col2:
                supplier = result_json.get("supplier_details", {})
                st.write("**Supplier Details**")
                st.write(f"Name: {supplier.get('name', 'N/A')}")
                st.write(f"Address: {supplier.get('address', 'N/A')}")
                status = supplier.get("validation_status", "N/A")
                st.markdown(f"Status: <span class='{get_status_style(status)}'>{status}</span>", unsafe_allow_html=True)

        # Provide JSON viewer at the end
        with st.expander("📋 View Raw JSON", expanded=False):
            st.json(result_json)
