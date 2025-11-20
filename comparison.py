# ui/comparison.py
import streamlit as st
import pandas as pd
from typing import Dict, Any, List
from services.explainability import explain_field
import os


def flatten_validation(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Create a flat list of:
    { validation_item, expected_value, extracted_value, status }
    """

    rows = []

    def add(item, expected, extracted, status):
        rows.append({
            "validation_item": item,
            "expected_value": expected or "",
            "extracted_value": extracted or "",
            "status": status or "N/A"
        })

    # Template Classification
    tpl = result.get("template_classification", {})
    add("Template.Type", "IT | Non-IT | Marketing", tpl.get("type"), tpl.get("confidence"))

    # Allianz Details
    allianz = result.get("allianz_details", {})
    add("Allianz.Address",
        "Allianz SE or Allianz Technology SE, Königinstrasse 28, 80802 München",
        allianz.get("address"),
        allianz.get("validation_status"))

    # Supplier Details
    supp = result.get("supplier_details", {})
    add("Supplier.Name", "Supplier name as written in the contract",
        supp.get("name"), supp.get("validation_status"))

    add("Supplier.Address", "Supplier legal address",
        supp.get("address"), supp.get("validation_status"))

    # Customer Contact
    cust = result.get("customer_contact", {})
    add("Customer.Email", "Must contain @allianz domain",
        cust.get("e-mail address"), cust.get("validation_status"))

    # VAT
    vat = result.get("vat", {})
    add("VAT.Option", "Tax affinity | Local contractor | Foreign contractor",
        vat.get("marked_option"), vat.get("validation_status"))

    # Terms
    terms = result.get("terms_and_termination", {})
    add("Contract.StartDate", "YYYY-MM-DD", terms.get("start_date"), terms.get("validation_status"))
    add("Contract.EndDate", "YYYY-MM-DD", terms.get("end_date"), terms.get("validation_status"))

    # Signatures
    sig = result.get("signature_verification", {})
    add("Signatures.Total", "According to business rules",
         sig.get("total_signatures"), sig.get("validation_status"))

    # Remuneration
    rem = result.get("remuneration_details", {})
    for idx, opt in enumerate(rem.get("marked_options", []), start=1):
        extracted = f"{opt.get('option')} {opt.get('amount','')} {opt.get('currency','')}"
        add(f"Remuneration.Option_{idx}", "Option must match selected model",
            extracted, rem.get("validation_status"))

    return rows


def render_comparison(result: Dict[str, Any], openai_client) -> None:
    st.subheader("🔍 Extracted vs Expected — Comparison Table")

    rows = flatten_validation(result)
    df = pd.DataFrame(rows)

    # Render rows as detailed list so each row can have an Explain button
    for i, row in df.iterrows():
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 3, 3, 2, 2])
            with col1:
                st.write(f"**{row['validation_item']}**")
            with col2:
                st.write(row["expected_value"])
            with col3:
                st.write(row["extracted_value"])
            with col4:
                st.write(row["status"])

            # Button for explainability
            if row["status"] in ["Mismatch", "Missing"]:
                btn_key = f"explain_{i}"
                if st.button("Explain", key=btn_key):
                    explanation = explain_field(
                        openai_client=openai_client,
                        model_name=os.getenv("AZURE_OPENAI_MODEL"),
                        field_name=row["validation_item"],
                        extracted_value=row["extracted_value"],
                        expected_value=row["expected_value"],
                        status=row["status"]
                    )
                    st.info(explanation)

        st.markdown("---")

    # CSV export
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download Comparison CSV",
        data=csv,
        file_name="contract_comparison.csv",
        mime="text/csv"
    )
