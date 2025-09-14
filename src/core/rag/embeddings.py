# src/core/rag/embeddings.py
"""
Embeddings Wrapper Module using Gemini API.

Provides an interface to generate embeddings for text chunks. Supports:
1. Gemini API (via content generation) as a pseudo-embedding
2. Fallback local embedding (deterministic hashing)

Example usage:
---------------
>>> from core.rag.embeddings import embed_texts
>>> texts = ["Hello world", "Test document"]
>>> vectors = embed_texts(texts)
>>> len(vectors), len(vectors[0])
(2, 16)
"""

import os
import hashlib
from typing import List

from config.llm_config import load_llm_config

try:
    from google import genai as gemini
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

VECTOR_DIM = 16  # fixed FAISS dimension

def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate vector embeddings for a list of text strings using Gemini API.

    Args:
        texts: List of strings to embed.

    Returns:
        List of numeric vectors (List[List[float]]). Length of vectors = VECTOR_DIM.
    """
    cfg = load_llm_config()
    vectors: List[List[float]] = []

    def text_to_vector(text: str) -> List[float]:
        """Convert text to deterministic vector of length VECTOR_DIM."""
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        # Slice hash into VECTOR_DIM chunks
        chunks = [h[i*(len(h)//VECTOR_DIM):(i+1)*(len(h)//VECTOR_DIM)] for i in range(VECTOR_DIM)]
        vec = [int(c, 16)/0xFFFFFFFFFFFFFFFF for c in chunks]  # normalize
        return vec

    if cfg.use_llm and cfg.provider.lower() == "gemini" and GEMINI_AVAILABLE:
        client = gemini.Client()
        for text in texts:
            try:
                prompt = f"Provide a concise summary or embedding-like representation of this text:\n{text}"
                response = client.models.generate_content(
                    model=getattr(cfg, "embedding_model", "gemini-2.5-flash"),
                    contents=prompt
                )
                # Convert response text to fixed-length vector
                vec = text_to_vector(response.text)
                vectors.append(vec)
            except Exception as e:
                raise RuntimeError(f"Failed to generate Gemini embeddings: {e}")
    else:
        # Fallback deterministic embedding
        for text in texts:
            vec = text_to_vector(text)
            vectors.append(vec)

    return vectors


if __name__ == "__main__":
    # Example usage
    sample_texts = ["Hello world", "CQIA embeddings test"]
    vecs = embed_texts(sample_texts)
    for i, v in enumerate(vecs):
        print(f"Text {i}: vector length={len(v)} -> {v}")
