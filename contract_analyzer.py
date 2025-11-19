import json
import os
import time
from typing import Tuple, Dict, Any

class ContractAnalyzer:
    """
    Uses Azure OpenAI to analyze contract text according to the provided prompt template
    and return a JSON object matching the schema in the prompt.
    """

    def __init__(self, client):
        self.client = client
        self.model = os.getenv("AZURE_OPENAI_MODEL")

    def analyze(self, text: str) -> Tuple[Dict[str, Any], float]:
        """
        Send the system prompt (from prompt_template.txt) and the contract text to the model.
        Returns (result_json, analysis_time_seconds).
        """
        # Load prompt template file (should be present in project root)
        prompt_path = os.path.join(os.getcwd(), "prompt_template.txt")
        if not os.path.exists(prompt_path):
            raise FileNotFoundError("prompt_template.txt not found in working directory.")

        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()

        user_message = f"""Please analyze the following contract document and extract the required information:

CONTRACT CONTENT:
---
{text}
---
Extract all required information according to the validation rules specified."""

        start_time = time.time()

        # Note: The exact call signature depends on the Azure OpenAI wrapper in use.
        # This mirrors your original code's usage: openai_client.chat.completions.create(...)
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=4096,
            temperature=0.3,
            model=self.model,
            response_format={"type": "json_object"}
        )

        analysis_time = time.time() - start_time

        # Parse model output content
        # The wrapper returns choices[0].message.content similar to your earlier usage
        content = response.choices[0].message.content
        if isinstance(content, (bytes, bytearray)):
            content = content.decode("utf-8")

        # Some model responses might already be JSON; attempt to parse
        try:
            result_json = json.loads(content)
        except json.JSONDecodeError as e:
            # Provide helpful error if JSON not parseable
            raise ValueError(f"Model did not return valid JSON. Error: {str(e)}. Raw content: {content[:1000]}")

        return result_json, analysis_time
