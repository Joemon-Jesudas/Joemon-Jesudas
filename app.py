import streamlit as st
from config import AppConfig
from services.azure_clients import AzureClientManager
from services.document_extractor import DocumentExtractor
from services.contract_analyzer import ContractAnalyzer
from ui.styles import Styles
from ui.display_manager import DisplayManager

def main():
    AppConfig.setup_page()
    Styles.load()

    st.title("📄 Document Validator System")

    if not AppConfig.validate():
        st.stop()

    azure = AzureClientManager()
    extractor = DocumentExtractor(azure.doc_client)
    analyzer = ContractAnalyzer(azure.openai_client)

    st.subheader("📤 Upload Document")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")

    if uploaded_file:
        DisplayManager.show_file_info(uploaded_file)

        if st.button("Analyze Document", type="primary"):
            pdf_bytes = uploaded_file.read()

            with st.spinner("Extracting text..."):
                text, pages, t_extract = extractor.extract_text(pdf_bytes)

            with st.spinner("Analyzing contract..."):
                result_json, t_analyze = analyzer.analyze(text)

            st.success("Document processed successfully!")
            DisplayManager.show_results(result_json)

if __name__ == "__main__":
    main()
