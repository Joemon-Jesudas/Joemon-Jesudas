import time

class DocumentExtractor:
    """Handles PDF → Text extraction using Azure Document Intelligence."""

    def __init__(self, client):
        self.client = client

    def extract_text(self, pdf_bytes: bytes):
        start = time.time()

        poller = self.client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=pdf_bytes
        )
        result = poller.result()

        full_text = "\n".join(
            line.content for page in result.pages for line in page.lines
        )

        extraction_time = time.time() - start
        return full_text, len(result.pages), extraction_time
