# services/explainability.py
from typing import Dict, Any
import os

EXPLAIN_PROMPT = """
You are an expert contract validation analyst. Given the following:
- Field Name
- Extracted Value
- Expected or Required Value
- Validation Status (Correct, Mismatch, Missing, N/A)

Explain clearly in 2–3 bullet points:
1. Why the model flagged the field with this status.
2. What the user must do to correct or improve the field.

Keep explanation short, neutral, and business-friendly.
"""

def explain_field(openai_client, model_name: str, field_name: str, extracted_value: str, expected_value: str, status: str) -> str:
    """
    Returns a short explanation from the LLM for why a field is mismatch/missing.
    """
    user_prompt = f"""
Field: {field_name}
Extracted Value: {extracted_value}
Expected/Required: {expected_value}
Status: {status}

Explain:
"""

    response = openai_client.chat.completions.create(
        messages=[
            {"role": "system", "content": EXPLAIN_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=250,
        temperature=0.2,
        model=model_name
    )

    return response.choices[0].message.content
