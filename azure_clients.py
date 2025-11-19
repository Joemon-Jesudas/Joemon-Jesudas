import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from openai import AzureOpenAI

load_dotenv()

class AzureClientManager:
    """Initializes and manages Azure OpenAI + Document Intelligence clients."""

    def __init__(self):
        self.doc_client = DocumentIntelligenceClient(
            endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"))
        )

        self.openai_client = AzureOpenAI(
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY")
        )
