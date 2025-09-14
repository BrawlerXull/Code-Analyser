"""
Pydantic schemas for the FastAPI app.
These define the structure of reports, issues, and metadata exchanged via the API.
"""

from pydantic import BaseModel
from typing import List, Optional


class ReportMeta(BaseModel):
    """Metadata about an analyzed repository."""

    path: str
    analyzed_at: str

    class Config:
        schema_extra = {
            "example": {
                "path": "/path/to/repo",
                "analyzed_at": "2025-09-14T12:34:56",
            }
        }


class IssueSchema(BaseModel):
    """Schema for an individual issue detected during analysis."""

    id: str
    category: str
    severity: str
    score: int
    file: str
    lineno: Optional[int]
    message: str
    suggested_fix: Optional[str]
    evidence: Optional[List[str]] = []

    class Config:
        schema_extra = {
            "example": {
                "id": "py001",
                "category": "style",
                "severity": "medium",
                "score": 5,
                "file": "src/app/main.py",
                "lineno": 42,
                "message": "Variable name not following snake_case convention.",
                "suggested_fix": "Rename variable to snake_case format.",
                "evidence": ["Line 42: myVariable = 10"],
            }
        }


class ReportSchema(BaseModel):
    """Schema for the full analysis report."""

    meta: ReportMeta
    summary: str
    overall_score: int
    issues: List[IssueSchema]
    recommendations: Optional[List[str]] = []

    class Config:
        schema_extra = {
            "example": {
                "meta": {
                    "path": "/path/to/repo",
                    "analyzed_at": "2025-09-14T12:34:56",
                },
                "summary": "The repository has good structure but needs improvement in naming conventions and test coverage.",
                "overall_score": 78,
                "issues": [
                    {
                        "id": "py001",
                        "category": "style",
                        "severity": "medium",
                        "score": 5,
                        "file": "src/app/main.py",
                        "lineno": 42,
                        "message": "Variable name not following snake_case convention.",
                        "suggested_fix": "Rename variable to snake_case format.",
                        "evidence": ["Line 42: myVariable = 10"],
                    }
                ],
                "recommendations": [
                    "Increase unit test coverage to above 80%",
                    "Adopt consistent naming conventions across modules",
                ],
            }
        }
