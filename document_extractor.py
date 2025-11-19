import time
from typing import Tuple

class DocumentExtractor:
    """
    Handles PDF -> text extraction using Azure Document Intelligence prebuilt-layout model.
    """

    def __init__(self, client):
        self.client = client

    def extract_text(self, pdf_bytes: bytes) -> Tuple[str, int, float]:
        """
        Extract text from PDF bytes.
        Returns tuple: (full_text, page_count, extraction_time_seconds)
        """
        start_time = time.time()

        # Begin analysis
        poller = self.client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=pdf_bytes
        )
        result = poller.result()

        # Safely build full text from pages and lines
        full_text_parts = []
        page_count = 0
        if getattr(result, "pages", None):
            pages = result.pages
            page_count = len(pages)
            for page in pages:
                if getattr(page, "lines", None):
                    for line in page.lines:
                        # Some line objects might not have content attribute in some SDK versions
                        content = getattr(line, "content", None)
                        if content:
                            full_text_parts.append(content)

        full_text = "\n".join(full_text_parts)
        extraction_time = time.time() - start_time
        return full_text, page_count, extraction_time
