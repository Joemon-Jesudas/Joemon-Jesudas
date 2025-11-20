# services/rag.py
import os
import time
import numpy as np
from typing import List, Dict, Any, Tuple

# Utility: cosine similarity
def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

class SimpleRAG:
    """
    Lightweight RAG: chunk text, create embeddings via AzureOpenAI client, store in-memory,
    and retrieve top_k relevant chunks by cosine similarity.
    """

    def __init__(self, openai_client, embedding_model: str | None = None):
        self.client = openai_client
        self.model = embedding_model or os.getenv("AZURE_OPENAI_EMBEDDING_MODEL") or os.getenv("AZURE_OPENAI_MODEL")
        # index: list of dicts {embedding: np.array, text: str, meta: {...}}
        self.index: List[Dict[str, Any]] = []

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Chunk the document text into overlapping chunks of chunk_size characters.
        Returns list of dicts {id, text, start, end}.
        """
        chunks = []
        start = 0
        length = len(text)
        idx = 0
        while start < length:
            end = min(start + chunk_size, length)
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"id": f"chunk_{idx}", "text": chunk_text, "start": start, "end": end})
                idx += 1
            if end == length:
                break
            start = end - overlap
        return chunks

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        Use AzureOpenAI embedding endpoint to create embeddings for a list of texts.
        This function assumes the client has `embeddings.create` method similar to OpenAI SDK.
        """
        # Some Azure wrappers require a different call signature; adapt if needed.
        # Attempt to call client.embeddings.create with model and input
        try:
            resp = self.client.embeddings.create(model=self.model, input=texts)
            embeddings = [np.array(item.embedding, dtype=np.float32) for item in resp.data]
            return embeddings
        except Exception as e:
            # try alternative path (older SDKs)
            # fallback: call as attribute
            raise RuntimeError(f"Embedding request failed: {e}")

    def build_index_from_text(self, doc_text: str, doc_meta: Dict[str, Any] = None, chunk_size: int = 1000, overlap: int = 200):
        """
        Clears and rebuilds index from `doc_text`.
        doc_meta: optional metadata (filename, pages, etc.)
        """
        self.index = []
        chunks = self.chunk_text(doc_text, chunk_size=chunk_size, overlap=overlap)
        texts = [c["text"] for c in chunks]
        if not texts:
            return
        embeddings = self.embed_texts(texts)
        for c, emb in zip(chunks, embeddings):
            entry = {
                "id": c["id"],
                "text": c["text"],
                "start": c["start"],
                "end": c["end"],
                "embedding": emb,
                "meta": doc_meta or {}
            }
            self.index.append(entry)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Returns top_k index entries most similar to query.
        """
        if not self.index:
            return []
        # create embedding for query
        q_emb = self.embed_texts([query])[0]
        # compute similarities
        sims = []
        for entry in self.index:
            sim = _cosine_sim(q_emb, entry["embedding"])
            sims.append((sim, entry))
        sims.sort(key=lambda x: x[0], reverse=True)
        top = [entry for _, entry in sims[:top_k]]
        return top

    def index_size(self) -> int:
        return len(self.index)
