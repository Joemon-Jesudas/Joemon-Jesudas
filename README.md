# 📄 Contract Validator System (Azure Document Intelligence + Azure OpenAI)

The **Contract Validator System** is a production-grade, Streamlit-based application that automatically:

✔ Extracts text from PDF contracts using **Azure Document Intelligence**  
✔ Analyzes and validates contract content using **Azure OpenAI (GPT-4o / 4.1 / 4o-mini)**  
✔ Highlights mismatches, missing fields, wrong patterns  
✔ Exports results to JSON, text, and **Excel validation reports**  
✔ Provides a clean UI for business users  

This project follows best engineering practices:
- Class-based modular architecture  
- Separation of concerns (services, UI, utils)  
- Clear extensibility  
- Testability  
- Easy deployment  

---

## 🔧 Features

### 📝 PDF Extraction  
Uses Azure Document Intelligence `prebuilt-layout` to extract page-wise text.

### 🤖 LLM-Based Validation  
Azure OpenAI analyzes the extracted text using a detailed validation prompt.

### 🟢 Red/Amber/Green Validation  
| Status | Meaning |
|--------|---------|
| **Correct** | Matched expected value |
| **Mismatch** | Value exists but incorrect |
| **Missing** | Required value missing |
| **N/A** | Not applicable |

### 📊 Excel Export  
Exports a unified Excel sheet with:  
- validation_item  
- extracted_value  
- status  

---

## 🏗️ Project Structure

```
contract_validator_app/
│
├── app.py
├── config.py
├── prompt_template.txt
│
├── services/
│   ├── azure_clients.py
│   ├── document_extractor.py
│   └── contract_analyzer.py
│
├── ui/
│   ├── styles.py
│   └── display_manager.py
│
└── utils/
    └── validators.py
```

---

## 🔑 Environment Variables (`.env`)

```
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=
AZURE_DOCUMENT_INTELLIGENCE_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_MODEL=gpt-4.1
```

---

## ▶️ Running the App

Install dependencies:

```
pip install -r requirements.txt
```

Start the app:

```
streamlit run app.py
```

---

## 📦 Excel Export

Generates a downloadable Excel validation report with columns:

- validation_item  
- extracted_value  
- status  

---

## 🏢 About This Project

This application is designed as an **enterprise-ready** solution for contract governance, procurement validation, and compliance workflows.

Made with ❤️ using Streamlit, Azure Document Intelligence, and Azure OpenAI.
