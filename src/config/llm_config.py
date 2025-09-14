# src/config/llm_config.py
"""
LLM and Vector Store Configuration

This module reads configuration from environment variables, provides safe defaults,
and returns a dataclass with all relevant settings.

⚠️ Privacy / Cost Notice:
When use_llm=True, repository code may be sent to an external provider (e.g., OpenAI),
which may incur cost and privacy considerations. Ensure you have permission before enabling.
"""

import os
import dataclasses
from typing import Optional, Dict


@dataclasses.dataclass
class LLMConfig:
    use_llm: bool
    provider: str  # 'openai' | 'local' | 'none'
    openai_api_key: Optional[str]
    embedding_model: str
    llm_model: str
    vector_store: str  # 'faiss' | 'disk'
    faiss_index_path: str
    max_chunk_size: int
    chunk_overlap: int
    local_embedding_path: Optional[str] = None


def load_llm_config() -> LLMConfig:
    """
    Load LLM and vector store configuration from environment variables.

    Environment Variables:
        USE_LLM (default: "false")
        LLM_PROVIDER (default: "openai")
        OPENAI_API_KEY
        EMBEDDING_MODEL (default: "text-embedding-3-small")
        LLM_MODEL (default: "gpt-4o-mini")
        VECTOR_STORE (default: "disk")
        FAISS_INDEX_PATH (default: "./data/faiss.index")
        MAX_CHUNK_SIZE (default: 1000)
        CHUNK_OVERLAP (default: 100)
        LOCAL_EMBEDDING_PATH (default: None)

    Returns:
        LLMConfig: Fully populated configuration object.
    """
    use_llm_env = os.getenv("USE_LLM", "false").lower()
    use_llm = use_llm_env in ("1", "true", "yes")

    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    vector_store = os.getenv("VECTOR_STORE", "disk").lower()
    faiss_index_path = os.getenv("FAISS_INDEX_PATH", "./data/faiss.index")

    max_chunk_size = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
    chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "100"))
    local_embedding_path = os.getenv("LOCAL_EMBEDDING_PATH")

    return LLMConfig(
        use_llm=use_llm,
        provider=provider,
        openai_api_key=openai_api_key,
        embedding_model=embedding_model,
        llm_model=llm_model,
        vector_store=vector_store,
        faiss_index_path=faiss_index_path,
        max_chunk_size=max_chunk_size,
        chunk_overlap=chunk_overlap,
        local_embedding_path=local_embedding_path,
    )


if __name__ == "__main__":
    cfg = load_llm_config()
    print("LLM Config Loaded:")
    print(dataclasses.asdict(cfg))
