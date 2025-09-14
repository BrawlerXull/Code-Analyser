from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from core.analyzers.manager import analyze_repo
from core.storage import init_db, save_report, get_report_by_id
from core.services.qa_service import answer_question
from core.services.job_manager import job_manager

import uvicorn


class AnalyzeRequest(BaseModel):
    path: str
    languages: Optional[List[str]] = ["py", "js"]
    run_async: Optional[bool] = False
    use_llm: Optional[bool] = False
    index_for_rag: Optional[bool] = False


class AnalyzeResponse(BaseModel):
    report_id: int
    overall_score: int
    summary: str


class QARequest(BaseModel):
    report_id: int
    question: str


class QAResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: str


app = FastAPI(title="CQIA - Code Quality Intelligence Agent")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database on startup."""
    init_db()


@app.post("/analyze")
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Analyze a repository path synchronously or asynchronously.
    """
    if request.run_async:
        job_id = job_manager.start_job(
            path=request.path,
            languages=request.languages,
            background=True,
            index_for_rag=request.index_for_rag,
            use_llm=request.use_llm,
        )
        return {"job_id": job_id, "status": "queued"}

    try:
        analysis = analyze_repo(
            path=request.path,
            languages=request.languages,
            index_for_rag=request.index_for_rag,
            use_llm=request.use_llm,
        )
        report_id = save_report(analysis)
        return AnalyzeResponse(
            report_id=report_id,
            overall_score=analysis.get("overall_score", 0),
            summary=analysis.get("summary", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports/{report_id}")
async def get_report(report_id: int):
    """
    Retrieve a report by its ID.
    """
    try:
        report = get_report_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
        return report
    except Exception:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")


@app.post("/qa")
async def qa(request: QARequest):
    """
    Answer a natural-language question about a report.
    """
    report = get_report_by_id(request.report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {request.report_id} not found")

    answer = answer_question(report, request.question)
    return QAResponse(**answer)


if __name__ == "__main__":
    uvicorn.run("src.app.main:app", host="0.0.0.0", port=8000, reload=True)
