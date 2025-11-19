import streamlit as st
from utils.validators import get_status_style

class DisplayManager:

    @staticmethod
    def show_file_info(uploaded_file):
        size_mb = uploaded_file.size / (1024 * 1024)
        st.metric("File Name", uploaded_file.name)
        st.metric("File Size", f"{size_mb:.2f} MB")

    @staticmethod
    def show_results(result_json):
        st.subheader("📊 Extraction Results")

        with st.expander("Template Classification", expanded=True):
            t = result_json["template_classification"]
            st.write(f"Type: **{t['type']}**")
            st.write("Keywords:", t["keywords_found"])

        with st.expander("Party Information", expanded=True):
            a = result_json["allianz_details"]
            st.write(f"Allianz: {a['address']}")
            st.markdown(
                f"Status: <span class='{get_status_style(a['validation_status'])}'>"
                f"{a['validation_status']}</span>",
                unsafe_allow_html=True
            )

        st.divider()
        st.json(result_json)
