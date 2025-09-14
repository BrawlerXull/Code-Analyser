"""
Pytest tests for the reporter module.

These tests validate issue standardization and overall report generation.
"""

import pytest
from core.reporter import generate_report, standardize_issue


def test_standardize_issue_defaults():
    """
    Ensure that standardize_issue fills missing fields and maps severity to score.
    """
    raw_issue = {
        "id": "JS-SEC-001",
        "category": "security",
        "severity": "high",
        "file": "app.js",
        "lineno": 10,
        "message": "Use of eval() detected"
    }

    issue = standardize_issue(raw_issue)

    assert issue["id"] == "JS-SEC-001", "Expected issue id to be preserved"
    assert issue["severity"] == "high", "Expected severity to be preserved"
    assert isinstance(issue["score"], int), "Expected score to be an integer"
    assert issue["score"] >= 70, "Expected high severity to default to score >= 70"


def test_generate_report_basic():
    """
    Ensure that generate_report produces a well-formed report
    with overall_score, recommendations, and markdown summary.
    """
    analysis = {
        "meta": {"path": "dummy_path", "analyzed_at": "2025-01-01T00:00:00"},
        "issues": [
            {
                "id": "PY-SEC-001",
                "category": "security",
                "severity": "critical",
                "file": "a.py",
                "lineno": 5,
                "message": "Dangerous use of eval()"
            },
            {
                "id": "JS-SEC-002",
                "category": "security",
                "severity": "low",
                "file": "b.js",
                "lineno": 20,
                "message": "Use of innerHTML detected"
            }
        ],
        "files": {"a.py": {}, "b.js": {}}
    }

    report = generate_report(analysis)

    assert isinstance(report["overall_score"], int), "Expected overall_score to be an integer"
    assert "recommendations" in report, "Expected recommendations in report"
    assert isinstance(report["recommendations"], list), "Expected recommendations to be a list"
    assert "markdown" in report, "Expected markdown key in report"
    assert "# Code Quality Report" in report["markdown"], "Expected markdown to contain header"
