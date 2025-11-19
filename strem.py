import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import streamlit as st
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult
from openai import AzureOpenAI

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Contract Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stAlert {
        border-radius: 0.5rem;
    }
    .header-section {
        padding: 1.5rem 0;
        border-bottom: 2px solid #f0f0f0;
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .validation-correct {
        color: #28a745;
        font-weight: bold;
    }
    .validation-mismatch {
        color: #ffc107;
        font-weight: bold;
    }
    .validation-missing {
        color: #dc3545;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_azure_clients() -> tuple:
    """
    Initialize Azure clients for Document Intelligence and OpenAI.
    Uses cached resource to avoid recreating clients on every run.
    """
    doc_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    doc_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    openai_key = os.getenv("AZURE_OPENAI_API_KEY")
    openai_version = os.getenv("AZURE_OPENAI_API_VERSION")
    
    doc_client = DocumentIntelligenceClient(
        endpoint=doc_endpoint,
        credential=AzureKeyCredential(doc_key)
    )
    
    openai_client = AzureOpenAI(
        api_version=openai_version,
        azure_endpoint=openai_endpoint,
        api_key=openai_key
    )
    
    return doc_client, openai_client


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.
    Returns True if all variables are present, False otherwise.
    """
    required_vars = [
        "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
        "AZURE_DOCUMENT_INTELLIGENCE_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_MODEL"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error("❌ Missing Environment Variables")
        st.write("The following environment variables are required in your `.env` file:")
        for var in missing_vars:
            st.write(f"- `{var}`")
        return False
    
    return True


def extract_text_from_pdf(pdf_content: bytes, doc_client: DocumentIntelligenceClient) -> tuple[str, int]:
    """
    Extract text from PDF using Azure Document Intelligence.
    Returns extracted text and number of pages processed.
    """
    try:
        start_time = time.time()
        
        poller = doc_client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=pdf_content
        )
        result = poller.result()
        
        full_text = ""
        page_count = 0
        
        if result.pages:
            page_count = len(result.pages)
            for page_num, page in enumerate(result.pages, 1):
                if page.lines:
                    for line in page.lines:
                        full_text += line.content + "\n"
        
        extraction_time = time.time() - start_time
        return full_text, page_count, extraction_time
    
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def analyze_contract(full_text: str, openai_client: AzureOpenAI) -> Dict[str, Any]:
    """
    Analyze contract using Azure OpenAI with structured JSON output.
    Returns parsed JSON response.
    """
    system_prompt = """You are a contract analysis expert. Extract and validate contract information 
according to the following requirements:

1. TEMPLATE CLASSIFICATION: Determine if the contract is IT, Non-IT (Consulting), or Marketing based on:
   - Non-IT: Look for "Consulting Agreement" header and keywords: Consulting, teaching, advising, coaching
   - IT: Look for "Agreement for IT Projects and Services" header and IT-related keywords
   - Marketing: Look for keywords: Marketing, Market Insight, Media
   Return the template type and detected keywords.

2. PARTY INFORMATION: Extract Name and address of Allianz and Supplier details:
   - For Allianz: Validate against these exact addresses:
     * "Allianz SE Königinstrasse 28, 80802 München Germany" or
     * "Allianz Technology SE Königinstrasse 28, 80802 München Germany"
     If one of the above is found return "Correct", If different format: "Mismatch", If not found: "Missing"
   - For Supplier: Extract name and address as provided. If not found: "Missing"

3. CUSTOMER CONTACT:
   - Extract customer contact details such as:
       1. Surname, First name, Telephone number and e-mail address.
       2. Validate that email contains "Allianz" domain otherwise, 'Mismatch' should be shown
          
4. Contractor´s Project Manager:  
   - Extract Contractor´s Project Manager details such as:
     1. Surname, First name, Telephone number and e-mail address.
     2. If a field is blank, the result should indicate 'Missing.' If the email address does not contain the supplier name(mentioned in PARTY INFORMATION), 
        it should show 'Mismatch'. 

5. PLACE OF PERFORMANCE:
   - If "Others" option is crossed (☒): Return the provided details, or "Missing" if blank
   - If first option (e.g., "the seat of the customer") is crossed ☒: Return "Correct"

6. SUBCONTRACTORS DETAILS:
   - Extract all provided details.

7. REMUNERATION DETAILS:
   - Identify which remuneration option is marked (checkboxes ☒):
   - Extract: marked_option, amount, currency
   - Validation Rules:
     * If Option 1 (Fixed price) is marked: Validate amount and currency are provided, status = "Correct" if both present, else "Missing"
     * If Option 2 is marked: Check if Attachment 3 (Rate Card) exists with rates defined in table. If table is not updated or Attachment 3 has no rates, status = "Missing", else status = "Correct"
     * If Option 3 is marked: Check if upper limit amount and currency are provided AND table is updated. If table is not updated or upper limit is missing, status = "Missing", else status = "Correct"
     * If multiple options marked, validate each marked option meets its requirements
     * If remuneration details are completely absent, status = "Missing"
   - Return marked options as array, provide table/rate details if present
   
8. INVOICING:
   - Identify which invoicing option is marked (checkboxes ☒):
     * Option 1: Monthly in arrears
     * Option 2: After overall acceptance
     * Option 3: Following acceptance of milestones
   - Extract: marked_option
   - Validation Rules:
     * If Remuneration part marked "Fixed price" (Option 1): Then one of the invoicing options ( 2, or 3) MUST be marked. If none marked, status = "Mismatch"
     * If Remuneration part marked "Remuneration based on time expended" (Option 2 or 3): Then invoicing can be any of the three options (1, 2, or 3). If none marked, status = "Missing"
   - Cross-validate with Remuneration selection
   - If invoicing details are completely absent, status = "Missing"

9. VAT (Value Added Tax):
   - Identify which VAT option is marked (checkboxes):
     * Option 1: VAT does not apply due to the tax affinity
     * Option 2: To the aforementioned costs the applicable rate of value-added tax shall be added – local Contractor
     * Option 3: The recipient of these services is liable to the VAT due (reverse charge) – foreign Contractor
   - Extract: marked_option
   - Validation Rules (based on Supplier details from section 2):
     * If Supplier is intercompany entity (Metafinanz, Kaiser X, Syncier): Option 1 MUST be marked, else status = "Mismatch"
     * If Supplier is located in Germany: Option 2 (local contractor) MUST be marked, else status = "Mismatch"
     * If Supplier is NOT located in Germany (foreign): Option 3 (reverse charge) MUST be marked, else status = "Mismatch"
     * If VAT section is missing, status = "Missing"
   - Cross-validate with supplier location and type
   - Provide validation_reason explaining the logic

10. INVOICE ADDRESS:
   - Extract invoice address (street, city, country) if "Invoice address" or "Invoice send to address" header is present
   - Validation Rules:
     * If header is present: Validate address matches one of:
       - Customer OE address from first page (Allianz SE or Allianz Technology SE with same address as in PARTY INFORMATION)
       - Standard address: "Dieselstraße 8, 85774 Unterföhring, Germany"
     * If header matches one of these addresses: status = "Correct"
     * If header exists but address does not match: status = "Mismatch"
     * If header is not present in contract: status = "Missing"
   - Provide matched_address and validation_reason

11. APPLICABILITY OF DATA PROTECTION, INFORMATION SECURITY, AND OUTSOURCING:
   - For each checkbox area (Data protection, Information security, Outsourcing):
     * Identify if checkbox is marked "Yes" or "No"
     * If marked "Yes": Check if corresponding document/attachment is included in the contract
       - If document is included: status = "Correct" or "Available"
       - If document is NOT included: status = "Missing"
     * If marked "No": status = "N/A" (not applicable)
     * If checkbox is not marked or section missing: status = "Missing"
   - Return individual status for each category (data_protection, information_security, outsourcing)
   - Provide document_status and validation_reason for each

12. TERMS AND TERMINATION:
   - This is a MANDATORY field
   - Extract: start_date, end_date (format: YYYY-MM-DD or as provided)
   - Validation Rules:
     * Both start_date and end_date MUST be provided
     * If either date is missing: status = "Missing"
     * If both dates are present: status = "Correct"
     * Calculate contract_duration (multiyear check: does contract span more than one calendar year?)
   - Return: start_date, end_date, contract_duration, is_multiyear (true/false), validation_status

13. VERIFICATION OF SIGNATURES:
   - Count and identify all signatures in the contract
   - Extract: total_signature_count, allianz_signature_count, supplier_signature_count, gsp_approval_present (true/false)
   - Determine required_signature_count based on business rules:
     * Rule 1: If Allianz SE is the buyer (first page): Requires 3 signatures (2 Allianz + 1 Supplier)
     * Rule 2: If project term is multiyear (more than one calendar year from section 11): Requires 3 signatures (2 Allianz + 1 Supplier)
     * Rule 3: If contract is Vendor Consolidation (check CWID number reference): Requires 4 signatures (GSP approval + 2 Allianz + 1 Supplier)
     * Rule 4: If contract is Non-IT category (from section 1): Requires 3 signatures (2 Allianz + 1 Supplier)
   - Validation Rules:
     * If actual signatures match required signatures: status = "Correct"
     * If actual signatures do NOT match required: status = "Mismatch"
     * If signatures cannot be verified or counted: status = "Missing"
   - Return: signature_counts, required_count, applied_rules, validation_status, validation_reason
   

Return response as JSON object matching the following schema:
{
    "template_classification": {
        "type": "IT|Non-IT|Marketing",
        "keywords_found": ["list of detected keywords"],
        "confidence": "High|Medium|Low"
    },
    "allianz_details": {
        "name": "extracted name",
        "address": "extracted address",
        "validation_status": "Correct|Mismatch|Missing"
    },
    "supplier_details": {
        "name": "extracted name or Missing",
        "address": "extracted address or Missing",
        "validation_status": "Correct|Mismatch|Missing"
    },
    "customer_contact": {
        "Surname": "surname or Missing",
        "First name": "First name or Missing",
        "Telephone number": "Telephone Number or Missing",
        "e-mail address": "email or Missing",
        "validation_status": "Correct|Mismatch|Missing"
    },
    "contractor_project_manager": {
       "Surname": "surname or Missing",
        "First name": "First name or Missing",
        "Telephone number": "Telephone Number or Missing",
        "e-mail address": "email or Missing",
        "validation_status": "Correct|Mismatch|Missing"
    },
    "place_of_performance": {
        "type": "Checked option (☒)",
        "details": "provided details or Missing",
        "validation_status": "Correct|Not found"
    },
    "subcontractor_details": {
        "present": true|false,
        "details": "provide details or null"
        "validation_status": "Found|Not found"
    },
    "remuneration_details": {
        "marked_options": [
            {
                "option": "return marked_option",
                "amount": "amount or Missing",
                "currency": "currency or Missing",
                "upper_limit": "upper limit amount or N/A",
                "rate_card_status": "Present|Missing|N/A",
                "table_status": "Updated|Not updated|N/A"
            }
        ],
        "validation_status": "Correct|Mismatch|Missing",
        "validation_reason": "Explanation of validation status"
    },
    "invoicing": {
        "marked_options": [
            {
                "option": "Monthly in arrears|After overall acceptance|Following milestone acceptance",
            }
        ],
        "validation_status": "Correct|Mismatch|Missing",
        "validation_reason": "Explanation including cross-validation with remuneration",
        "cross_validation_with_remuneration": "Matches|Does not match remuneration selection"
    },
    "vat": {
        "marked_option": "Tax affinity|Local contractor|Foreign contractor (reverse charge)|Missing",
        "validation_status": "Correct|Mismatch|Missing",
        "validation_reason": "Explanation based on supplier location and type",
        "expected_option": "Expected VAT option based on supplier details"
    },
    "invoice_address": {
        "address_present": true|false,
        "extracted_address": "extracted address or N/A",
        "matched_address": "Customer OE|Standard Unterföhring|None",
        "validation_status": "Correct|Mismatch|Missing",
        "validation_reason": "Explanation of address validation"
    },
    "data_protection_security_outsourcing": {
        "data_protection": {
            "marked": "Yes|No|Missing",
            "document_included": true|false,
            "validation_status": "Correct|Available|Missing|N/A",
            "validation_reason": "Explanation"
        },
        "information_security": {
            "marked": "Yes|No|Missing",
            "document_included": true|false,
            "validation_status": "Correct|Available|Missing|N/A",
            "validation_reason": "Explanation"
        },
        "outsourcing": {
            "marked": "Yes|No|Missing",
            "document_included": true|false,
            "validation_status": "Correct|Available|Missing|N/A",
            "validation_reason": "Explanation"
        }
    },
    "terms_and_termination": {
        "start_date": "date or Missing",
        "end_date": "date or Missing",
        "contract_duration": "duration in months/years",
        "is_multiyear": true|false,
        "validation_status": "Correct|Missing",
        "validation_reason": "Mandatory field - explanation"
    },
    "signature_verification": {
        "total_signatures": 0,
        "allianz_signatures": 0,
        "supplier_signatures": 0,
        "gsp_approval_present": true|false,
        "required_signatures": 0,
        "applied_rules": ["list of rules that determine required signatures"],
        "validation_status": "Correct|Mismatch|Missing",
        "validation_reason": "Detailed explanation of signature requirement logic"
    },
}
"""
    
    user_message = f"""Please analyze the following contract document and extract the required information:

CONTRACT CONTENT:
---
{full_text}
---

Extract all required information according to the validation rules specified."""
    
    try:
        start_time = time.time()
        
        response = openai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=4096,
            temperature=0.3,
            model=os.getenv("AZURE_OPENAI_MODEL"),
            response_format={"type": "json_object"}
        )
        
        analysis_time = time.time() - start_time
        result_json = json.loads(response.choices[0].message.content)
        
        return result_json, analysis_time
    
    except Exception as e:
        raise Exception(f"Failed to analyze contract: {str(e)}")


def get_validation_style(status: str) -> str:
    """Return CSS class for validation status."""
    if status == "Correct" or status == "Found":
        return "validation-correct"
    elif status == "Mismatch" or status == "Not found":
        return "validation-mismatch"
    else:
        return "validation-missing"


def display_extraction_results(result: Dict[str, Any]) -> None:
    """Display extracted contract information in organized sections."""
    
    # Template Classification
    with st.expander("📋 Template Classification", expanded=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            template_type = result.get("template_classification", {}).get("type", "N/A")
            st.metric("Contract Type", template_type)
        with col2:
            keywords = result.get("template_classification", {}).get("keywords_found", [])
            confidence = result.get("template_classification", {}).get("confidence", "N/A")
            st.write(f"**Confidence:** {confidence}")
            # st.write(f"**Keywords Found:** {', '.join(keywords) if keywords else 'None'}")
    
    # Party Information
    with st.expander("🏢 Party Information", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Allianz Details**")
            allianz = result.get("allianz_details", {})
            st.write(f"Name: {allianz.get('name', 'N/A')}")
            st.write(f"Address: {allianz.get('address', 'N/A')}")
            status = allianz.get("validation_status", "N/A")
            st.markdown(f"Status: <span class='{get_validation_style(status)}'>{status}</span>", 
                       unsafe_allow_html=True)
        
        with col2:
            st.write("**Supplier Details**")
            supplier = result.get("supplier_details", {})
            st.write(f"Name: {supplier.get('name', 'N/A')}")
            st.write(f"Address: {supplier.get('address', 'N/A')}")
            status = supplier.get("validation_status", "N/A")
            st.markdown(f"Status: <span class='{get_validation_style(status)}'>{status}</span>", 
                       unsafe_allow_html=True)
    
    # Customer Contact
    with st.expander("👤 Customer Contact", expanded=True):
        customer = result.get("customer_contact", {})
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Surname:** {customer.get('Surname', 'N/A')}")
            st.write(f"**First Name:** {customer.get('First name', 'N/A')}")
        
        with col2:
            st.write(f"**Telephone:** {customer.get('Telephone number', 'N/A')}")
            st.write(f"**Email:** {customer.get('e-mail address', 'N/A')}")
        
        status = customer.get("validation_status", "N/A")
        st.markdown(f"**Status:** <span class='{get_validation_style(status)}'>{status}</span>", 
                   unsafe_allow_html=True)
    
    # Contractor's Project Manager
    with st.expander("👨‍💼 Contractor's Project Manager", expanded=True):
        contractor = result.get("contractor_project_manager", {})
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Surname:** {contractor.get('Surname', 'N/A')}")
            st.write(f"**First Name:** {contractor.get('First name', 'N/A')}")
        
        with col2:
            st.write(f"**Telephone:** {contractor.get('Telephone number', 'N/A')}")
            st.write(f"**Email:** {contractor.get('e-mail address', 'N/A')}")
        
        status = contractor.get("validation_status", "N/A")
        st.markdown(f"**Status:** <span class='{get_validation_style(status)}'>{status}</span>", 
                   unsafe_allow_html=True)
    
    # Place of Performance
    with st.expander("📍 Place of Performance", expanded=True):
        place = result.get("place_of_performance", {})
        st.write(f"**Selected Option:** {place.get('type', 'N/A')}")
        details = place.get('details', 'N/A')
        if isinstance(details, dict):
            # Render as table
            details_table = "| Field | Value |\n|-------|-------|\n"
            for k, v in details.items():
                details_table += f"| {k} | {v} |\n"
            st.markdown(details_table)
        elif isinstance(details, str):
            st.write(f"**Details:** {details}")
        else:
            st.write("**Details:** N/A")

    
    # Subcontractor Details
    with st.expander("🤝 Subcontractor Details", expanded=True):
        subcontractor = result.get("subcontractor_details", {})
        present = subcontractor.get("present", False)
        st.write(f"**Present:** {'Yes' if present else 'No'}")
        if present:
            st.write(f"**Details:** {subcontractor.get('details', 'N/A')}")

    with st.expander("💰 Remuneration Details", expanded=True):
        remuneration = result.get("remuneration_details", {})
    
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("**Marked Options:**")
            for option in remuneration.get("marked_options", []):
                st.write(f"- {option.get('option', 'N/A')}")
                if option.get('amount') != 'N/A' and option.get('amount') != 'Missing':
                    st.write(f"  Amount: {option.get('amount', 'N/A')} {option.get('currency', 'N/A')}")
                if option.get('rate_card_status') != 'N/A':
                    st.write(f"  Rate Card: {option.get('rate_card_status', 'N/A')}")
    
        with col2:
            status = remuneration.get("validation_status", "N/A")
            st.markdown(f"**Status:** <span class='{get_validation_style(status)}'>{status}</span>", 
                    unsafe_allow_html=True)
        
        st.info(remuneration.get("validation_reason", "No details"))

    # Invoicing
    with st.expander("📧 Invoicing", expanded=True):
        invoicing = result.get("invoicing", {})
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("**Marked Options:**")
            for option in invoicing.get("marked_options", []):
                st.write(f"- {option.get('option', 'N/A')}")
                if option.get('milestone_details') and option.get('milestone_details') != 'N/A':
                    st.write(f"  Milestones: {option.get('milestone_details', 'N/A')}")
        
        with col2:
            status = invoicing.get("validation_status", "N/A")
            st.markdown(f"**Status:** <span class='{get_validation_style(status)}'>{status}</span>", 
                    unsafe_allow_html=True)
        
        st.write(f"**Cross-Validation:** {invoicing.get('cross_validation_with_remuneration', 'N/A')}")
        st.info(invoicing.get("validation_reason", "No details"))


        # VAT
    with st.expander("💶 VAT (Value Added Tax)", expanded=True):
        vat = result.get("vat", {})
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write(f"**Marked Option:** {vat.get('marked_option', 'N/A')}")
            st.write(f"**Expected Option:** {vat.get('expected_option', 'N/A')}")
        
        with col2:
            status = vat.get("validation_status", "N/A")
            st.markdown(f"**Status:** <span class='{get_validation_style(status)}'>{status}</span>", 
                    unsafe_allow_html=True)
        
        st.info(vat.get("validation_reason", "No details"))

    # Invoice Address
    with st.expander("📮 Invoice Address", expanded=True):
        invoice = result.get("invoice_address", {})
        
        if invoice.get("address_present"):
            st.write(f"**Extracted Address:** {invoice.get('extracted_address', 'N/A')}")
            st.write(f"**Matched With:** {invoice.get('matched_address', 'None')}")
        
        status = invoice.get("validation_status", "N/A")
        st.markdown(f"**Status:** <span class='{get_validation_style(status)}'>{status}</span>", 
                unsafe_allow_html=True)
        st.info(invoice.get("validation_reason", "No details"))

    # Data Protection, Security, Outsourcing
    with st.expander("🔒 Data Protection, Information Security & Outsourcing", expanded=True):
        dps = result.get("data_protection_security_outsourcing", {})
        
        for category, label in [
            ("data_protection", "Data Protection"),
            ("information_security", "Information Security"),
            ("outsourcing", "Outsourcing")
        ]:
            st.write(f"**{label}:**")
            cat_data = dps.get(category, {})
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"Marked: {cat_data.get('marked', 'N/A')}")
            with col2:
                st.write(f"Document: {'Yes' if cat_data.get('document_included') else 'No'}")
            with col3:
                status = cat_data.get("validation_status", "N/A")
                st.markdown(f"<span class='{get_validation_style(status)}'>{status}</span>", 
                        unsafe_allow_html=True)
            
            st.caption(cat_data.get("validation_reason", ""))
            st.divider()

    # Terms and Termination
    with st.expander("📅 Terms and Termination", expanded=True):
        terms = result.get("terms_and_termination", {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Start Date", terms.get("start_date", "Missing"))
        with col2:
            st.metric("End Date", terms.get("end_date", "Missing"))
        with col3:
            st.metric("Duration", terms.get("contract_duration", "N/A"))
        
        st.write(f"**Multiyear Contract:** {'Yes' if terms.get('is_multiyear') else 'No'}")
        
        status = terms.get("validation_status", "N/A")
        st.markdown(f"**Status:** <span class='{get_validation_style(status)}'>{status}</span>", 
                unsafe_allow_html=True)
        st.info(terms.get("validation_reason", "No details"))

    # Signature Verification
    with st.expander("✍️ Signature Verification", expanded=True):
        sig = result.get("signature_verification", {})
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Signatures", sig.get("total_signatures", 0))
        with col2:
            st.metric("Allianz", sig.get("allianz_signatures", 0))
        with col3:
            st.metric("Supplier", sig.get("supplier_signatures", 0))
        with col4:
            st.metric("Required", sig.get("required_signatures", 0))
        
        st.write(f"**GSP Approval Present:** {'Yes' if sig.get('gsp_approval_present') else 'No'}")
        st.write(f"**Applied Rules:** {', '.join(sig.get('applied_rules', []))}")
        
        status = sig.get("validation_status", "N/A")
        st.markdown(f"**Status:** <span class='{get_validation_style(status)}'>{status}</span>", 
                unsafe_allow_html=True)
        st.info(sig.get("validation_reason", "No details"))



def main():
    """Main application function."""
    
    # Header Section
    st.markdown("""
        <div class="header-section">
            <h1>📄 Document Validator System</h1>
            <p>Automated extraction and analysis of contract documents using Azure AI services</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Sidebar - Configuration and Information
    with st.sidebar:
        # st.image("allianz_logo.png", width=180, caption="Allianz", use_column_width=False)
        # OR (if you want it to be left justified and top aligned with some spacing)
        st.sidebar.markdown(
            '''
            <div style="padding-bottom: 12px;">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Allianz.svg/2560px-Allianz.svg.png"
                    width="160" style="padding:5px 0;" />
            </div>
            ''', unsafe_allow_html=True
        )
        st.header("ℹ️ Application Info")
        st.info(
            "**Document Validator v1.0**\n\n"
            "This application uses Azure Document Intelligence to extract text from PDFs "
            "and Azure OpenAI to analyze contract content automatically."
        )
        
        st.divider()
        st.subheader("📊 Processing Statistics")
        if "processing_time" in st.session_state:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Extraction Time", f"{st.session_state.extraction_time:.2f}s")
            with col2:
                st.metric("Analysis Time", f"{st.session_state.analysis_time:.2f}s")
            st.metric("Pages Processed", st.session_state.page_count)
            st.caption(f"Processed: {st.session_state.processing_time}")
    
    # Validate environment
    if not validate_environment():
        st.stop()
    
    # Initialize session state
    if "processing_complete" not in st.session_state:
        st.session_state.processing_complete = False
        st.session_state.result = None
        st.session_state.file_name = None
    
    # File Upload Section
    st.subheader("📤 Upload Document")
    uploaded_file = st.file_uploader(
        "Select a PDF document to analyze",
        type="pdf",
        help="Upload a contract document in PDF format"
    )
    
    if uploaded_file is not None:
        # File information
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", uploaded_file.name)
        with col2:
            st.metric("File Size", f"{file_size_mb:.2f} MB")
        
        # File size validation
        if file_size_mb > 50:
            st.warning("⚠️ File size exceeds 50 MB. Processing may take longer.")
        
        # Process Document Section
        st.subheader("🔄 Process Document")
        
        col1, col2 = st.columns(2)
        
        with col1:
            process_button = st.button(
                "🚀 Analyze Document",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            clear_button = st.button(
                "🔄 Clear Results",
                use_container_width=True
            )
        
        if clear_button:
            st.session_state.processing_complete = False
            st.session_state.result = None
            st.session_state.file_name = None
            st.rerun()
        
        if process_button:
            try:
                # Get Azure clients
                doc_client, openai_client = get_azure_clients()
                
                # Read PDF content
                pdf_content = uploaded_file.read()
                
                # Create progress containers
                status_container = st.empty()
                progress_bar = st.progress(0)
                
                # Extract text from PDF
                status_container.info("📖 Extracting text from PDF...")
                progress_bar.progress(33)
                
                full_text, page_count, extraction_time = extract_text_from_pdf(
                    pdf_content, doc_client
                )
                
                st.session_state.extraction_time = extraction_time
                st.session_state.page_count = page_count
                
                # Analyze contract
                status_container.info("🔍 Analyzing contract with AI...")
                progress_bar.progress(66)
                
                result, analysis_time = analyze_contract(full_text, openai_client)
                
                st.session_state.analysis_time = analysis_time
                st.session_state.processing_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.result = result
                st.session_state.file_name = uploaded_file.name
                st.session_state.processing_complete = True
                
                # Update progress
                progress_bar.progress(100)
                status_container.empty()
                
                # Success message
                st.markdown("""
                    <div class="success-box">
                    ✅ <b>Document processed successfully!</b>
                    </div>
                """, unsafe_allow_html=True)
                
            except Exception as e:
                st.error("❌ Error Processing Document")
                with st.expander("View Error Details"):
                    st.code(str(e), language="text")
    
    # Display Results
    if st.session_state.processing_complete and st.session_state.result:
        st.divider()
        st.subheader("📊 Extraction Results")
        
        # Display organized results
        display_extraction_results(st.session_state.result)
        
        # Raw JSON Display
        st.divider()
        with st.expander("📋 View Raw JSON", expanded=False):
            st.json(st.session_state.result)
        
        # Download Results
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            json_str = json.dumps(st.session_state.result, indent=2)
            st.download_button(
                label="⬇️ Download Results (JSON)",
                data=json_str,
                file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col2:
            csv_export = json.dumps(st.session_state.result, indent=2)
            st.download_button(
                label="⬇️ Download Results (Text)",
                data=csv_export,
                file_name=f"contract_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    # Footer
    st.divider()
    footer_col1, footer_col2, footer_col3 = st.columns(3)
    with footer_col1:
        st.caption("📝 Contract Analyzer v1.0")
    with footer_col2:
        st.caption(f"🕐 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    with footer_col3:
        st.caption("🔒 Enterprise Grade | Production Ready")


if __name__ == "__main__":
    main()
