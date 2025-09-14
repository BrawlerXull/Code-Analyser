# src/core/agent/agent_controller.py
"""
Agent Controller for CQIA (Gemini version)

Orchestrates multi-step workflows such as explaining issues, generating
fix plans, and optionally interacting with an LLM using a vector store.

Supports:
- LLM explanations via Gemini if configured
- Retrieval-Augmented Generation via VectorStore
- Fallback templated explanations without LLM

Example usage:
---------------
>>> from core.agent.agent_controller import AgentController
>>> agent = AgentController()
>>> report = get_report_by_id(1)
>>> explanation = agent.explain_issue(report, "PY-SEC-001")
>>> print(explanation["explanation"])
"""

import os
import json
from typing import Dict, Any, List, Optional

from config.llm_config import load_llm_config
from core.rag.retriever import retrieve, VectorStore, build_corpus_from_repo, index_repo
from core.services.qa_service import answer_question



class AgentController:
    """
    Controller class for running multi-step agent workflows over reports with Gemini LLM support.
    """

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize the AgentController.

        Args:
            config: Optional LLMConfig instance. If None, load from environment.
        """
        self.config = config or load_llm_config()
        self.use_llm = getattr(self.config, "use_llm", False)

        # Initialize vector store if LLM is enabled
        self.vector_store: Optional[VectorStore] = None
        if self.use_llm:
            index_path = getattr(self.config, "faiss_index_path", "./data/faiss.index")
            self.vector_store = VectorStore(index_path=index_path)

    def explain_issue(self, report: Dict, issue_id: str) -> Dict:
        """
        Explain a specific issue using Gemini LLM and relevant code context.

        Args:
            report: Report dict from generate_report or get_report_by_id
            issue_id: ID of the issue to explain

        Returns:
            Dict with explanation, step-by-step fix, sources, and confidence
        """
        issue = next((i for i in report.get("issues", []) if i.get("id") == issue_id), None)
        if not issue:
            return {"issue_id": issue_id, "explanation": "Issue not found.",
                    "fix_plan": [], "sources": [], "confidence": "low"}

        sources: List[str] = []

        # Retrieve relevant code chunks
        context_text = ""
        if self.use_llm and self.vector_store:
            query = f"{issue.get('category')}: {issue.get('message')}"
            hits = retrieve(query, self.vector_store, top_k=3)
            for hit in hits:
                context_text += hit["text"] + "\n"
                sources.append(hit["meta"].get("file", "?"))

        # Build prompt
        prompt = f"""
You are a code quality assistant. Analyze the following issue and code context:

Issue: {issue.get('message')}
Category: {issue.get('category')}
Severity: {issue.get('severity')}
File: {issue.get('file')} Line: {issue.get('lineno')}
Code Context:
{context_text}

Provide:
1. A concise explanation of the issue.
2. Step-by-step fix plan as a numbered list.
Respond in JSON: {{"explanation": "...", "fix_plan": ["step 1", "step 2"]}}
"""

        # Call LLM or fallback
        if self.use_llm:
            try:
                llm_resp = self._call_llm(prompt)
                parsed = json.loads(llm_resp)
                return {
                    "issue_id": issue_id,
                    "explanation": parsed.get("explanation", issue.get("message")),
                    "fix_plan": parsed.get("fix_plan", []),
                    "sources": sources,
                    "confidence": "high"
                }
            except Exception:
                return {
                    "issue_id": issue_id,
                    "explanation": issue.get("message"),
                    "fix_plan": [f"Review {issue.get('file')} line {issue.get('lineno')}"],
                    "sources": sources,
                    "confidence": "medium"
                }
        else:
            return {
                "issue_id": issue_id,
                "explanation": issue.get("message"),
                "fix_plan": [f"Review {issue.get('file')} line {issue.get('lineno')}"],
                "sources": sources,
                "confidence": "medium"
            }

    def generate_patch_suggestion(self, report: Dict, issue_id: str) -> Dict:
        """
        Attempt to produce a code patch suggestion for an issue.

        Args:
            report: Report dict
            issue_id: Issue identifier

        Returns:
            Dict containing suggested patch text and confidence
        """
        issue = next((i for i in report.get("issues", []) if i.get("id") == issue_id), None)
        if not issue:
            return {"issue_id": issue_id, "suggested_patch": "", "confidence": "low"}

        prompt = f"""
Generate a code patch suggestion for the following issue:

Issue: {issue.get('message')}
File: {issue.get('file')} Line: {issue.get('lineno')}
"""
        if self.use_llm:
            try:
                patch = self._call_llm(prompt)
                return {"issue_id": issue_id, "suggested_patch": patch, "confidence": "high"}
            except Exception:
                return {"issue_id": issue_id, "suggested_patch": f"Manually fix {issue.get('file')} line {issue.get('lineno')}", "confidence": "medium"}
        else:
            return {"issue_id": issue_id, "suggested_patch": f"Manually fix {issue.get('file')} line {issue.get('lineno')}", "confidence": "medium"}

    def _call_llm(self, prompt: str) -> str:
        """
        Internal LLM call helper using Gemini (Google Generative AI).

        Args:
            prompt: Text prompt to send to the model.

        Returns:
            LLM-generated text

        Raises:
            RuntimeError if LLM usage is not configured.
        """
        if not self.use_llm:
            raise RuntimeError("LLM usage is disabled in configuration.")

        if getattr(self.config, "provider", "").lower() == "gemini":

            # Initialize Gemini client (reads GEMINI_API_KEY from env)
            import google.generativeai as gemini
            client = gemini.Client()

            model_name = getattr(self.config, "llm_model", "gemini-2.5-flash")

            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                # The text is in response.text
                return response.text
            except Exception as e:
                raise RuntimeError(f"Gemini API call failed: {e}")

        else:
            raise RuntimeError(f"LLM provider {self.config.provider} not supported.")
