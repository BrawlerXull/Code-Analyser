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
    import google.generativeai as gemini
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate vector embeddings for a list of text strings using Gemini API.

    Args:
        texts: List of strings to embed.

    Returns:
        List of numeric vectors (List[List[float]]). Length of vectors = 16.

    Behavior:
        - If cfg.use_llm and provider=='gemini' and Gemini SDK available:
            Calls Gemini content generation endpoint and hashes response text to produce numeric vector.
        - Else:
            Fallback: deterministic local embedding via hashing (length=16 floats).

    Notes:
        - Local fallback is NOT suitable for semantic search; it is only to keep pipeline functional offline.
        - Using Gemini may incur cost; ensure GEMINI_API_KEY is set.
    """
    cfg = load_llm_config()
    vectors: List[List[float]] = []

    if cfg.use_llm and cfg.provider.lower() == "gemini" and GEMINI_AVAILABLE:
        client = gemini.Client()  # reads GEMINI_API_KEY from env
        for text in texts:
            try:
                prompt = f"Provide a concise summary or embedding-like representation of this text:\n{text}"
                response = client.models.generate_content(
                    model=getattr(cfg, "embedding_model", "gemini-2.5-flash"),
                    contents=prompt
                )
                # Convert response text to pseudo-vector via hashing
                h = hashlib.sha256(response.text.encode("utf-8")).hexdigest()
                chunks = [h[i*8:(i+1)*8] for i in range(16)]
                vec = [int(c, 16)/0xFFFFFFFF for c in chunks]
                vectors.append(vec)
            except Exception as e:
                raise RuntimeError(f"Failed to generate Gemini embeddings: {e}")
    else:
        # Fallback: deterministic pseudo-vectors via hashing
        for text in texts:
            h = hashlib.sha256(text.encode("utf-8")).hexdigest()
            chunks = [h[i*8:(i+1)*8] for i in range(16)]
            vec = [int(c, 16)/0xFFFFFFFF for c in chunks]
            vectors.append(vec)

    return vectors


if __name__ == "__main__":
    # Example usage
    sample_texts = ["Hello world", "CQIA embeddings test"]
    vecs = embed_texts(sample_texts)
    for i, v in enumerate(vecs):
        print(f"Text {i}: vector length={len(v)} -> {v}")
