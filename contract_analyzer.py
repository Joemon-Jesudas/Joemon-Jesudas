import os
import time
import json

class ContractAnalyzer:
    """Analyzes contract text using Azure OpenAI LLM."""

    def __init__(self, client):
        self.client = client
        self.model = os.getenv("AZURE_OPENAI_MODEL")

    def analyze(self, text: str):
        with open("prompt_template.txt", "r") as f:
            system_prompt = f.read()

        start = time.time()

        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this contract:\n\n{text}"}
            ],
            model=self.model,
            max_tokens=4096,
            response_format={"type": "json_object"}
        )

        analysis_time = time.time() - start
        result_json = json.loads(response.choices[0].message.content)
        return result_json, analysis_time
