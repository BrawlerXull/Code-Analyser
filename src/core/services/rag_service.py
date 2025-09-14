from typing import List, Dict, Any
import faiss
import os
import pickle
import numpy as np

from config.llm_config import load_llm_config
from core.agent.agent_controller import AgentController  # Gemini LLM + embeddings


class RAGService:
    def __init__(self, index_path: str = None):
        self.cfg = load_llm_config()
        self.index_path = index_path or self.cfg.faiss_index_path
        self.index: faiss.IndexFlatL2 | None = None
        self.documents: List[Dict[str, Any]] = []

        if os.path.exists(self.index_path):
            self.load_index()
        else:
            self.index = None

    def build_index(self, docs: List[Dict[str, Any]]):
        self.documents = docs
        agent = AgentController(self.cfg)
        embeddings = []

        for doc in docs:
            emb = agent.embed_text(doc["text"])  # Gemini embeddings
            embeddings.append(emb)

        if not embeddings:
            raise ValueError("No embeddings generated. Check documents or Gemini API.")

        dim = len(embeddings[0])
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(np.array(embeddings, dtype="float32"))

        # Save index + docs
        faiss.write_index(self.index, self.index_path)
        with open(self.index_path + ".docs.pkl", "wb") as f:
            pickle.dump(self.documents, f)


    def load_index(self):
        """Load FAISS index and document metadata."""
        self.index = faiss.read_index(self.index_path)
        with open(self.index_path + ".docs.pkl", "rb") as f:
            self.documents = pickle.load(f)


    def query(self, question: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve top-K documents relevant to the question using Gemini embeddings.
        """
        if self.index is None:
            raise ValueError("RAG index not built or loaded.")

        agent = AgentController(self.cfg)
        q_vec = np.array([agent.embed_text(question)], dtype="float32")
        D, I = self.index.search(q_vec, top_k)
        results = [self.documents[i] for i in I[0] if i < len(self.documents)]
        return results
    
    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Use retrieved code chunks + Gemini LLM to answer question.
        """
        retrieved = self.query(question, top_k=5)
        context_text = "\n".join([doc["text"] for doc in retrieved])

        agent = AgentController(self.cfg)
        resp = agent.ask({"context": context_text}, question)

        return {
            "answer": resp.get("answer", ""),
            "sources": [doc.get("meta", {}).get("file") for doc in retrieved],
            "confidence": resp.get("confidence", "medium")
        }

