import re
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# -------------------------------------------------------
# 1. Azure Document Intelligence Setup
# -------------------------------------------------------

endpoint = "<YOUR_DOCUMENT_INTELLIGENCE_ENDPOINT>"
key = "<YOUR_KEY>"

client = DocumentAnalysisClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
)

# -------------------------------------------------------
# 2. Read PDF using Prebuilt OCR
# -------------------------------------------------------

def extract_full_text(pdf_path):
    with open(pdf_path, "rb") as f:
        poller = client.begin_analyze_document("prebuilt-read", document=f)
        result = poller.result()

    full_text = ""
    for page in result.pages:
        for line in page.lines:
            full_text += line.content + "\n"
    return full_text


# -------------------------------------------------------
# 3. Template Classification Logic
# -------------------------------------------------------

def classify_template(text):
    t = text.lower()

    if "agreement for it projects and services" in t:
        return "IT"

    if "consulting agreement" in t or any(
        w in t for w in ["consulting", "teaching", "advising", "coaching"]
    ):
        return "Non-IT"

    if any(w in t for w in ["marketing", "market insight", "media"]):
        return "Marketing"

    return "Unknown"


# -------------------------------------------------------
# 4. Generic Section Extraction Logic
# -------------------------------------------------------

def extract_between(text, start_words, end_words):
    start_pattern = "|".join([re.escape(w) for w in start_words])
    end_pattern = "|".join([re.escape(w) for w in end_words])

    pattern = rf"({start_pattern})(.*?)(?={end_pattern})"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    if match:
        return match.group(2).strip()

    return ""


# -------------------------------------------------------
# 5. All Sections Extraction
# -------------------------------------------------------

def extract_sections(text):

    sections = {}

    sections["template"] = classify_template(text)

    sections["allianz_address"] = extract_between(
        text,
        ["allianz", "allianz technology", "allianz services"],
        ["supplier", "central points", "project management", "place of performance"],
    )

    sections["supplier_address"] = extract_between(
        text,
        ["supplier", "vendor", "service provider"],
        ["central points", "project management", "place of performance"],
    )

    sections["central_poc"] = extract_between(
        text,
        ["central points of contact", "project management"],
        ["place of performance", "remuneration"],
    )

    sections["place_of_performance"] = extract_between(
        text,
        ["place of performance"],
        ["remuneration", "fees", "invoicing"],
    )

    sections["remuneration"] = extract_between(
        text,
        ["remuneration", "fees"],
        ["invoicing", "invoice address", "data protection"],
    )

    sections["invoicing"] = extract_between(
        text,
        ["invoicing"],
        ["invoice address", "data protection"],
    )

    sections["invoice_address"] = extract_between(
        text,
        ["invoice address"],
        ["data protection", "termination"],
    )

    sections["data_protection"] = extract_between(
        text,
        ["data protection"],
        ["terms", "termination", "signatures"],
    )

    sections["termination"] = extract_between(
        text,
        ["terms and termination", "termination"],
        ["signatures", "signed by"],
    )

    # Signature block – last page region
    signatures = re.findall(
        r"(signature|signed by|signatures)([\s\S]{0,500})",
        text,
        flags=re.IGNORECASE
    )
    sections["signatures"] = "\n".join([s[1].strip() for s in signatures]) or ""

    return sections


# -------------------------------------------------------
# 6. Generate Markdown Output
# -------------------------------------------------------

def generate_markdown(sections):
    return f"""
# Contract Extraction Summary

## 1. Template Used
**Category:** {sections['template']}

## 2. Allianz Name & Address
{sections['allianz_address']}

## 3. Supplier Name & Address
{sections['supplier_address']}

## 4. Central Points of Contact / Project Management
{sections['central_poc']}

## 5. Place of Performance
{sections['place_of_performance']}

## 6. Remuneration
{sections['remuneration']}

## 7. Invoicing
{sections['invoicing']}

## 8. Invoice Address
{sections['invoice_address']}

## 9. Data Protection
{sections['data_protection']}

## 10. Terms and Termination
{sections['termination']}

## 11. Signatures
{sections['signatures']}
"""


# -------------------------------------------------------
# 7. MAIN EXECUTION
# -------------------------------------------------------

if __name__ == "__main__":
    pdf_path = "contract.pdf"   # <<--- your file here

    full_text = extract_full_text(pdf_path)
    sections = extract_sections(full_text)
    markdown_output = generate_markdown(sections)

    print(markdown_output)

