# src/core/rag/retriever.py
"""
Retriever Module for CQIA RAG Pipeline

Prepares document chunks from a code repository, indexes them in a vector store,
and performs similarity-based retrieval for QA.

Example usage:
---------------
>>> from core.rag.retriever import VectorStore, build_corpus_from_repo, index_repo, retrieve
>>> store = VectorStore(index_path="./data/faiss.index")
>>> count = index_repo("./my-repo", store)
>>> results = retrieve("security vulnerability in utils.py", store, top_k=3)
>>> for r in results:
...     print(r["meta"], r["score"])
"""

import os
from pathlib import Path
from typing import List, Dict, Any

from core.rag.vector_storage import VectorStore
from core.utils import chunk_text, safe_read_text
from config.llm_config import load_llm_config


def build_corpus_from_repo(path: str, max_chunk: int = None) -> List[Dict[str, Any]]:
    """
    Walk through a repository and build chunked documents for vector indexing.

    Args:
        path: Path to repository
        max_chunk: Optional max characters per chunk (defaults to config)

    Returns:
        List of dicts: { "id": str, "text": str, "meta": {...} }

    Example return:
    [
        {"id": "src/app.py#0", "text": "...", "meta": {"file": "src/app.py", "start": 0}},
        {"id": "src/app.py#1", "text": "...", "meta": {"file": "src/app.py", "start": 500}},
    ]
    """
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    cfg = load_llm_config()
    max_chunk = max_chunk or cfg.max_chunk_size
    corpus: List[Dict[str, Any]] = []

    for root, dirs, files in os.walk(path):
        for file in files:
            if not file.endswith((".py", ".js")):
                continue
            file_path = Path(root) / file
            try:
                text = safe_read_text(file_path)
                chunks = chunk_text(text, chunk_size=max_chunk, overlap=cfg.chunk_overlap)
                for i, chunk in enumerate(chunks):
                    doc_id = f"{file_path.relative_to(path)}#{i}"
                    corpus.append({
                        "id": doc_id,
                        "text": chunk,
                        "meta": {"file": str(file_path.relative_to(path)), "start": i*max_chunk}
                    })
            except Exception as e:
                print(f"Warning: Failed to read {file_path}: {e}")

    return corpus


def index_repo(path: str, vector_store: VectorStore) -> int:
    """
    Index a repository in the vector store.

    Args:
        path: Path to repository
        vector_store: Instance of VectorStore

    Returns:
        Number of documents indexed
    """
    corpus = build_corpus_from_repo(path)
    vector_store.add_documents(corpus)
    vector_store.save()
    return len(corpus)


def retrieve(query: str, vector_store: VectorStore, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve top-k most relevant document chunks for a query.

    Args:
        query: Query string
        vector_store: Instance of VectorStore
        top_k: Number of top results to return

    Returns:
        List of dicts: { "text": str, "meta": dict, "score": float }

    Example:
        >>> results = retrieve("security vulnerability in utils.py", store, top_k=3)
        >>> for r in results:
        ...     print(r["meta"], r["score"])
    """
    hits = vector_store.query(query, top_k=top_k)
    results: List[Dict[str, Any]] = []
    for hit in hits:
        results.append({
            "text": hit["doc"]["text"],
            "meta": hit["doc"]["meta"],
            "score": hit["score"]
        })
    return results
