# src/core/rag/vector_store.py
"""
Vector Store Wrapper Module

Supports:
1. FAISS vector store (if installed)
2. Disk-backed JSONL fallback

Provides basic add, persist, load, and query functionality for text embeddings.

Example usage:
---------------
>>> from core.rag.vector_store import VectorStore
>>> store = VectorStore(index_path="./data/faiss.index", use_faiss=True)
>>> store.add_documents([{"id": "doc1", "text": "Hello world", "meta": {}}])
>>> store.save()
>>> results = store.query("Hello", top_k=1)
>>> print(results)
"""

import os
import json
import math
from typing import List, Dict, Any, Tuple
from config.llm_config import load_llm_config
from core.rag.embeddings import embed_texts

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class VectorStore:
    """
    Vector store with FAISS (if available) or disk-backed fallback.
    """

    def __init__(self, index_path: str = None, use_faiss: bool = True):
        self.cfg = load_llm_config()
        self.index_path = index_path or "./data/faiss.index"
        self.use_faiss = use_faiss and FAISS_AVAILABLE and self.cfg.use_llm
        self.documents: List[Dict[str, Any]] = []
        self.embeddings: List[List[float]] = []

        if self.use_faiss:
            self.dim = 16  # must match embed_texts output
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                if self.index.d != self.dim:
                    print(f"[WARNING] FAISS index dimension mismatch. Resetting index.")
                    self.index = faiss.IndexFlatL2(self.dim)
            else:
                self.index = faiss.IndexFlatL2(self.dim)
        else:
            self.index = None

    def add_documents(self, docs: List[Dict[str, Any]]) -> None:
        """
        Add documents to the store.
        Args:
            docs: List of dicts with keys: 'id', 'text', 'meta'.
        """
        texts = [doc["text"] for doc in docs]
        vecs = embed_texts(texts)
        self.documents.extend(docs)
        self.embeddings.extend(vecs)

        if self.use_faiss and self.index:
            import numpy as np
            self.index.add(np.array(vecs, dtype="float32"))

    def save(self) -> None:
        """Persist the vector store to disk."""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        if self.use_faiss and self.index:
            faiss.write_index(self.index, self.index_path)
            meta_path = self.index_path + ".meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2)
                print("saved at 1")
        else:
            # disk fallback
            data = [{"doc": doc, "embedding": emb} for doc, emb in zip(self.documents, self.embeddings)]
            with open(self.index_path, "w", encoding="utf-8") as f:
                for item in data:
                    f.write(json.dumps(item) + "\n")
                    print("saved at 2")

    def load(self) -> None:
        """Load vector store from disk."""
        if self.use_faiss and FAISS_AVAILABLE and os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            meta_path = self.index_path + ".meta.json"
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
        elif os.path.exists(self.index_path):
            self.documents = []
            self.embeddings = []
            with open(self.index_path, "r", encoding="utf-8") as f:
                for line in f:
                    item = json.loads(line)
                    self.documents.append(item["doc"])
                    self.embeddings.append(item["embedding"])

    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query vector store for most similar documents.
        Args:
            query_text: Query string
            top_k: Number of top results to return
        Returns:
            List of dicts: { "doc": {...}, "score": float }
        """
        query_vec = embed_texts([query_text])[0]

        if self.use_faiss and self.index and self.index.ntotal > 0:
            import numpy as np
            D, I = self.index.search(np.array([query_vec], dtype="float32"), top_k)
            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx < len(self.documents):
                    results.append({"doc": self.documents[idx], "score": float(dist)})
            return results
        else:
            # Linear scan fallback
            results: List[Tuple[float, Dict[str, Any]]] = []
            for doc, emb in zip(self.documents, self.embeddings):
                dot = sum(a*b for a, b in zip(query_vec, emb))
                norm_query = math.sqrt(sum(a*a for a in query_vec))
                norm_emb = math.sqrt(sum(b*b for b in emb))
                sim = dot / (norm_query * norm_emb + 1e-10)
                results.append((sim, doc))
            results.sort(key=lambda x: x[0], reverse=True)
            return [{"doc": d, "score": float(s)} for s, d in results[:top_k]]
