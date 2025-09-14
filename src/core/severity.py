# src/core/severity.py
"""
Automated Severity Scoring Module

This module converts raw issues into numeric scores, adjusts for file hotness
and historical weight, and computes overall repository quality score.

Example usage:
---------------
>>> from core.severity import compute_issue_score, enrich_issues_with_scores
>>> issue = {"id":"PY-SEC-001","severity":"high","occurrences":2,"file":"app.py"}
>>> score = compute_issue_score(issue, file_hotness=3)
>>> score
80
"""

from typing import Dict, Any, List
import math


def severity_to_base_score(severity: str) -> int:
    """
    Map textual severity to base numeric score.

    Args:
        severity: "critical" | "high" | "medium" | "low"

    Returns:
        int score (0-100)
    """
    mapping = {"critical": 95, "high": 75, "medium": 40, "low": 10}
    return mapping.get(severity.lower(), 40)


def compute_issue_score(issue: Dict[str, Any], file_hotness: int = 1, historical_weight: float = 1.0) -> int:
    """
    Compute a numeric score for a single issue.

    Args:
        issue: Issue dictionary with keys 'severity', 'occurrences', etc.
        file_hotness: Weight based on number of issues in the file.
        historical_weight: Multiplier for recurring issues.

    Returns:
        int score (0-100)
    """
    base = severity_to_base_score(issue.get("severity", "medium"))
    occurrences = issue.get("occurrences", 1)
    penalty = 10 * (occurrences - 1)
    hotness_factor = min(3, file_hotness)
    score = base + hotness_factor * 5 - penalty
    score = max(0, min(100, int(score * historical_weight)))
    return score


def compute_overall_score(issues: List[Dict], repo_size: int, trend_factor: float = 1.0) -> int:
    """
    Compute overall repo score based on individual issue scores.

    Args:
        issues: List of issue dicts with 'score' field
        repo_size: Number of files or size metric
        trend_factor: Weight factor for trend of issues (default 1.0)

    Returns:
        int overall score (0-100)
    """
    if not issues or repo_size <= 0:
        return 100

    avg_issue_score = sum(i.get("score", 40) for i in issues) / len(issues)
    normalized_penalty = (avg_issue_score / 100) * min(repo_size, 50)  # normalize penalty
    overall = 100 - normalized_penalty * trend_factor
    return max(0, min(100, int(overall)))


def enrich_issues_with_scores(issues: List[Dict], file_hotness_map: Dict[str, int]) -> List[Dict]:
    """
    Compute and add 'score' to each issue based on severity and file hotness.

    Args:
        issues: List of issue dicts
        file_hotness_map: Dict[file:str] = number of issues in that file

    Returns:
        List of enriched issue dicts with 'score' field
    """
    enriched = []
    for issue in issues:
        file_name = issue.get("file", "")
        hotness = file_hotness_map.get(file_name, 1)
        issue["score"] = compute_issue_score(issue, file_hotness=hotness)
        enriched.append(issue)
    return enriched
