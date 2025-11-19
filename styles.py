import streamlit as st

class Styles:
    """Loads CSS styles used across the app."""

    @staticmethod
    def load():
        st.markdown("""
        <style>
            .main { padding: 2rem; }
            .stAlert { border-radius: 0.5rem; }
            .validation-correct { color:#28a745; font-weight:bold; }
            .validation-mismatch { color:#ffc107; font-weight:bold; }
            .validation-missing { color:#dc3545; font-weight:bold; }
            .header-section { padding: 1.5rem 0; border-bottom: 2px solid #f0f0f0; margin-bottom: 2rem; }
            .success-box { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
            .error-box { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
            .info-box { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
        </style>
        """, unsafe_allow_html=True)
