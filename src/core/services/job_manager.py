"""
Job Manager for CQIA.

Provides facilities to start analysis jobs synchronously or asynchronously,
track their status, and retrieve results.

Example:
--------
>>> from core.services.job_manager import job_manager
>>> job_id = job_manager.start_job(path=".", languages=["py"], background=False)
>>> job_manager.get_job(job_id)
{'status': 'finished', 'created_at': ..., 'finished_at': ..., 'report_id': 1, 'params': {...}}
"""

import threading
import uuid
import datetime
from typing import Dict, Any

from core.analyzers.manager import analyze_repo
from core.storage import save_report, init_db


class JobManager:
    """
    Manage background or synchronous jobs for analyzing repositories.
    """

    def __init__(self) -> None:
        self.jobs: Dict[str, Dict[str, Any]] = {}
        init_db()

    def start_job(
        self,
        path: str,
        languages: list,
        background: bool = False,
        index_for_rag: bool = False,
        use_llm: bool = False,
    ) -> str:
        """
        Start a new analysis job.

        Args:
            path: Path to repository.
            languages: List of languages to analyze.
            background: Whether to run in background thread.
            index_for_rag: Whether to index the repo after analysis (RAG).
            use_llm: Whether to enable LLM/Gemini explanations.

        Returns:
            job_id string.
        """
        job_id = f"job-{uuid.uuid4().hex}"
        self.jobs[job_id] = {
            "status": "pending",
            "created_at": datetime.datetime.utcnow().isoformat(),
            "finished_at": None,
            "report_id": None,
            "params": {
                "path": path,
                "languages": languages,
                "index_for_rag": index_for_rag,
                "use_llm": use_llm,
            },
            "error": None,
        }

        if background:
            thread = threading.Thread(
                target=self._run_job,
                args=(job_id, path, languages, index_for_rag, use_llm),
                daemon=True,
            )
            thread.start()
        else:
            self._run_job(job_id, path, languages, index_for_rag, use_llm)

        return job_id

    def _run_job(
        self,
        job_id: str,
        path: str,
        languages: list,
        index_for_rag: bool = False,
        use_llm: bool = False,
    ) -> None:
        """
        Internal worker to run analysis and save report.
        """
        job = self.jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        try:
            analysis = analyze_repo(path, languages=languages, index_for_rag=index_for_rag, use_llm=use_llm)
            report_id = save_report(analysis)
            job["report_id"] = report_id

            # Optional RAG indexing
            if index_for_rag and use_llm:
                try:
                    from core.rag.retriever import index_repo
                    index_count = index_repo(path)
                    job["index_count"] = index_count
                except Exception as e:
                    job["index_error"] = str(e)

            job["status"] = "finished"
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
        finally:
            job["finished_at"] = datetime.datetime.utcnow().isoformat()

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get job details by id.

        Args:
            job_id: Job identifier.
        Returns:
            Job dict.
        """
        return self.jobs.get(job_id, {"status": "not_found", "job_id": job_id})


# Module-level singleton
job_manager = JobManager()
