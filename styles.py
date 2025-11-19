import streamlit as st

class Styles:
    @staticmethod
    def load():
        st.markdown("""
            <style>
                .validation-correct { color:#28a745; font-weight:bold; }
                .validation-mismatch { color:#ffc107; font-weight:bold; }
                .validation-missing { color:#dc3545; font-weight:bold; }
            </style>
        """, unsafe_allow_html=True)
