# services/explainability.py
import os

EXPLAIN_PROMPT = """
You are an expert contract validation analyst. Given:

- Field Name
- Extracted Value
- Expected/Required Value
- Validation Status (Correct, Mismatch, Missing, N/A)

Explain concisely in **2–3 bullet points**:
1. Why the field received this status.
2. What the user should do to fix or improve it.

Avoid long paragraphs. Keep the tone business-friendly.
"""


def explain_field(openai_client, model_name: str, field_name: str,
                  extracted_value: str, expected_value: str, status: str) -> str:

    user_prompt = f"""
Field Name: {field_name}
Extracted Value: {extracted_value}
Expected Value: {expected_value}
Status: {status}

Explain in 2–3 bullet points why this happened and how to fix it:
"""

    response = openai_client.chat.completions.create(
        messages=[
            {"role": "system", "content": EXPLAIN_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=250,
        temperature=0.1,
        model=model_name
    )

    return response.choices[0].message.content
