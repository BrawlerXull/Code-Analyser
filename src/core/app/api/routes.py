"""
API routes for the CQIA FastAPI app.

This module defines the REST API endpoints used for analyzing repositories,
fetching reports, and answering natural-language questions.

Endpoints:
- POST /api/analyze: Run an analysis on a repository.
- GET /api/reports/{report_id}: Retrieve a previously generated report.
- POST /api/qa: Ask questions about a report.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from core.storage import save_report, get_report_by_id
from core.analyzers.manager import analyze_repo
from core.services.qa_service import answer_question
from core.services.job_manager import job_manager

from app.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    QARequest,
    QAResponse,
    ReportSchema,
)

router = APIRouter(prefix="/api")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repo_endpoint(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Run analysis on a repository.

    - If `run_async=True`, schedules a background job and returns a job_id.
    - If synchronous, runs immediately and returns the report summary.

    Example response (async):
    ```json
    {
      "job_id": "job-123abc",
      "status": "queued"
    }
    ```

    Example response (sync):
    ```json
    {
      "report_id": 1,
      "overall_score": 82,
      "summary": "Good structure but missing type hints."
    }
    ```
    """
    if request.run_async:
        job_id = job_manager.start_job(request.path, request.languages, background=True)
        return {"job_id": job_id, "status": "queued"}

    try:
        report = analyze_repo(request.path, request.languages)
        report_id = save_report(report)
        return AnalyzeResponse(
            report_id=report_id,
            overall_score=report.get("overall_score", 0),
            summary=report.get("summary", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.get("/reports/{report_id}", response_model=ReportSchema)
async def get_report(report_id: int):
    """
    Fetch a previously generated report by ID.

    Example response:
    ```json
    {
      "meta": {"path": "/repo", "analyzed_at": "2025-09-14T12:34:56"},
      "summary": "Repo has strong documentation but low test coverage.",
      "overall_score": 75,
      "issues": [],
      "recommendations": ["Increase unit test coverage"]
    }
    ```
    """
    report = get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/qa", response_model=QAResponse)
async def qa_endpoint(request: QARequest):
    """
    Ask a natural-language question about a report.

    Example response:
    ```json
    {
      "answer": "The top 3 issues are related to missing docstrings, unused imports, and inconsistent naming.",
      "sources": ["src/app/main.py", "src/core/utils.py"],
      "confidence": "high"
    }
    ```
    """
    report = get_report_by_id(request.report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    result = answer_question(report, request.question)
    return QAResponse(**result)
