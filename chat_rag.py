# ui/chat_rag.py
import streamlit as st
from typing import Dict, Any, List
import os
import textwrap
from services.rag import SimpleRAG

SYSTEM_RAG_PROMPT = """You are a helpful contract assistant. Use ONLY the provided context (document excerpts) to answer. 
If the answer isn't present in the context, say: "I cannot find that information in the contract." Keep answers concise and cite the chunk id."""

def initialize_rag_state():
    if "rag_indexed" not in st.session_state:
        st.session_state.rag_indexed = False
    if "rag_meta" not in st.session_state:
        st.session_state.rag_meta = {}
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # {role, message}

def build_rag_if_needed(openai_client, full_text: str):
    initialize_rag_state()
    if st.session_state.rag_indexed:
        return
    rag = SimpleRAG(openai_client)
    rag.build_index_from_text(full_text, doc_meta={"source": st.session_state.get("file_name", "unknown")})
    st.session_state.rag_index = rag
    st.session_state.rag_indexed = True
    st.session_state.rag_meta = {"chunks": rag.index_size()}

def render_chat(openai_client, model_name: str):
    initialize_rag_state()

    if "result" not in st.session_state or not st.session_state.result:
        st.info("Process a document first (upload & analyze) to enable contract chat.")
        return

    # Ensure we have raw extracted text in result under _raw_extracted_text
    doc_text = st.session_state.result.get("_raw_extracted_text") or st.session_state.result.get("extracted_text", "")
    if not doc_text:
        # try to build from pages if present
        pages = st.session_state.result.get("pages", [])
        lines = []
        for p in pages:
            for line in p.get("lines", []):
                lines.append(line.get("content", ""))
        doc_text = "\n".join(lines)

    # Build RAG index (if not already)
    build_rag_if_needed(openai_client, doc_text)

    st.subheader("💬 Ask the Contract — RAG Chat")
    q = st.text_area("Enter your question", key="rag_input", height=120)

    # Controls
    col_left, col_right = st.columns([1, 3])
    with col_left:
        top_k = st.selectbox("Top K chunks", options=[1,2,3,4,5], index=2)
        max_context_chars = st.slider("Context chars per chunk", 100, 2000, 1000, step=100)
    with col_right:
        submit = st.button("Ask", key="rag_ask")

    # show history
    if st.session_state.chat_history:
        st.markdown("**Conversation**")
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f"**You:** {msg['message']}")
            else:
                st.markdown(f"**Assistant:** {msg['message']}")

    if submit:
        if not q.strip():
            st.warning("Please enter a question.")
            return

        st.session_state.chat_history.append({"role":"user", "message": q})
        rag: SimpleRAG = st.session_state.get("rag_index")
        # Retrieve top_k chunks
        retrieved = rag.retrieve(q, top_k=top_k)
        ctx_parts = []
        for r in retrieved:
            # optionally trim to a number of chars
            txt = r["text"][:max_context_chars]
            ctx_parts.append(f"CHUNK_ID: {r['id']}\n{txt}")

        system_prompt = SYSTEM_RAG_PROMPT
        user_prompt = f"QUESTION:\n{q}\n\nCONTEXT:\n{chr(10).join(ctx_parts)}"

        # Call model
        with st.spinner("Querying model..."):
            response = openai_client.chat.completions.create(
                messages=[
                    {"role":"system", "content": system_prompt},
                    {"role":"user", "content": user_prompt}
                ],
                model=model_name,
                max_tokens=512,
                temperature=0.0
            )
        answer = response.choices[0].message.content
        st.session_state.chat_history.append({"role":"assistant", "message": answer})
        # show the answer immediately
        st.markdown(f"**Assistant:** {answer}")

        # Also show which chunks were used
        st.markdown("**Retrieved chunks**")
        for r in retrieved:
            st.write(f"- {r['id']}: {r['text'][:200]}...")
