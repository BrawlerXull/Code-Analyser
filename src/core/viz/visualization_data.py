# src/core/viz/visualization_data.py
"""
Visualization Data Preparation Module

Prepares JSON payloads for front-end dashboards including:
- Dependency graph visualization
- Issue heatmaps by category
- Trend charts (recent analysis)

Example usage:
---------------
>>> from core.viz.visualization_data import build_dashboard_payload
>>> report = {
...     "overall_score": 78,
...     "files": {"app.py": {}, "utils.py": {}},
...     "issues": [
...         {"id":"PY-SEC-001","category":"security","score":90,"file":"app.py"},
...         {"id":"PY-COM-002","category":"complexity","score":40,"file":"utils.py"}
...     ],
...     "meta": {"path": "/repo/project","analyzed_at":"2025-09-14T10:00:00Z"}
... }
>>> payload = build_dashboard_payload(report)
>>> payload.keys()
dict_keys(['header', 'charts', 'dep_graph'])
"""

from typing import Dict, Any, List
import datetime
from core.dep_graph import build_dep_graph


def build_dashboard_payload(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build JSON payload for dashboard visualization from a report.

    Args:
        report: Canonical analysis report dict including issues, files, and metadata.

    Returns:
        Dict with keys:
            - header: overall_score, repo path, analyzed_at
            - charts: issues_by_category, top_hotspots, recent_trend
            - dep_graph: nodes/edges JSON
    """
    # Header info
    header = {
        "overall_score": report.get("overall_score", 0),
        "repo_path": report.get("meta", {}).get("path", "?"),
        "analyzed_at": report.get("meta", {}).get(
            "analyzed_at", datetime.datetime.utcnow().isoformat()
        ),
    }

    # Charts
    issues = report.get("issues", [])
    counts_by_category: Dict[str, int] = {}
    hotspots: Dict[str, int] = {}
    for issue in issues:
        cat = issue.get("category", "general")
        counts_by_category[cat] = counts_by_category.get(cat, 0) + 1
        file = issue.get("file")
        if file:
            hotspots[file] = max(hotspots.get(file, 0), issue.get("score", 0))

    # Top 10 hotspots
    top_hotspots = sorted(
        [{"id": k, "score": v} for k, v in hotspots.items()],
        key=lambda x: x["score"],
        reverse=True
    )[:10]

    # Placeholder recent trend
    recent_trend = []
    # if historical data is available in report['history'], can populate timeseries
    # For now, generate dummy last 7 days trend
    today = datetime.datetime.utcnow().date()
    for i in range(7):
        day = today - datetime.timedelta(days=i)
        recent_trend.append({"date": day.isoformat(), "score": report.get("overall_score", 0)})

    charts = {
        "issues_by_category": [{"category": k, "count": v} for k, v in counts_by_category.items()],
        "top_hotspots": top_hotspots,
        "recent_trend": recent_trend[::-1],  # chronological order
    }

    # Dependency graph
    dep_graph = build_dep_graph(report.get("meta", {}).get("path", "?"))

    payload = {
        "header": header,
        "charts": charts,
        "dep_graph": dep_graph
    }

    return payload


if __name__ == "__main__":
    # Example usage
    sample_report = {
        "overall_score": 85,
        "issues": [
            {"id": "PY-SEC-001", "category": "security", "score": 90, "file": "app.py"},
            {"id": "PY-COM-002", "category": "complexity", "score": 40, "file": "utils.py"},
        ],
        "files": {"app.py": {}, "utils.py": {}},
        "meta": {"path": "/repo/project", "analyzed_at": "2025-09-14T10:00:00Z"}
    }
    payload = build_dashboard_payload(sample_report)
    import json
    print(json.dumps(payload, indent=2))
