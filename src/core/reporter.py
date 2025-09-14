"""
reporter.py - Canonicalize analyzer issues and generate final reports.

This module provides utilities to normalize issues coming from analyzers
(Python, JavaScript, etc.), compute scores, generate recommendations, and
render human-readable reports (e.g., Markdown).
"""

from typing import Dict, Any, List
import datetime

from core.severity import enrich_issues_with_scores, compute_overall_score

# Optional LLM Agent support
try:
    from core.agent.agent_controller import AgentController
except Exception:
    AgentController = None


def standardize_issue(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a raw issue into a standardized schema.

    Args:
        raw (Dict[str, Any]): Raw issue from an analyzer.

    Returns:
        Dict[str, Any]: Standardized issue with consistent fields.
    """
    severity_level = raw.get("severity", "low").lower()
    severity_map = {"critical": 90, "high": 70, "medium": 40, "low": 10}
    score = raw.get("score", severity_map.get(severity_level, 10))

    standardized = {
        "id": raw.get("id", f"GEN-{hash(str(raw)) & 0xFFFF}"),
        "category": raw.get("category", "general"),
        "severity": severity_level,
        "score": int(score),
        "file": raw.get("file"),
        "lineno": raw.get("lineno"),
        "message": raw.get("message", "No description provided"),
        "suggested_fix": raw.get("suggested_fix", "Review and fix as appropriate"),
        "evidence": raw.get("evidence"),
    }
    return standardized


def generate_report(analysis: Dict[str, Any], config: Any = None) -> Dict[str, Any]:
    """
    Generate a canonical report from combined analysis.

    Args:
        analysis (Dict[str, Any]): Aggregated analysis from manager.analyze_repo.
        config (Any, optional): Optional configuration object (e.g., use_llm flag).

    Returns:
        Dict[str, Any]: Final report with standardized issues, recommendations, and markdown.
    """
    raw_issues: List[Dict[str, Any]] = analysis.get("issues", [])
    standardized_issues = [standardize_issue(i) for i in raw_issues]

    # Compute file hotness map (issue count per file)
    file_hotness_map: Dict[str, int] = {}
    for issue in standardized_issues:
        file_name = issue.get("file")
        if file_name:
            file_hotness_map[file_name] = file_hotness_map.get(file_name, 0) + 1

    # Enrich issues with scores
    issues = enrich_issues_with_scores(standardized_issues, file_hotness_map)

    # Compute overall score
    overall_score = compute_overall_score(issues, repo_size=len(analysis.get("files", {})))

    # Optionally call LLM Agent for top issues
    if AgentController is not None and getattr(config, "use_llm", False):
        try:
            agent = AgentController()
            top_issues = sorted(issues, key=lambda x: x["score"], reverse=True)[:3]
            for issue in top_issues:
                issue_id = issue["id"]
                try:
                    explanation = agent.explain_issue(analysis, issue_id)
                    issue["llm_explanation"] = explanation
                except Exception:
                    issue["llm_explanation"] = f"Top issue {issue_id}: {issue['message']}"
        except Exception:
            pass  # best-effort, fail silently

    # Recommendations from top issues
    recommendations: List[str] = []
    for issue in sorted(issues, key=lambda x: x["score"], reverse=True)[:5]:
        if issue["category"] == "security":
            rec = f"Address security issue in `{issue['file']}:{issue.get('lineno')}` - {issue['message']}."
        elif issue["category"] == "complexity":
            rec = f"Refactor function in `{issue['file']}` at line {issue.get('lineno')} to reduce complexity."
        elif issue["category"] == "duplication":
            rec = f"Remove duplicated code in `{issue['file']}`."
        elif issue["category"] == "testing":
            rec = f"Add missing tests in `{issue['file']}`."
        else:
            rec = f"Review issue in `{issue['file']}`: {issue['message']}."
        recommendations.append(rec)

    # Build summary
    summary = (
        f"Analyzed at {analysis.get('meta', {}).get('analyzed_at', datetime.datetime.utcnow().isoformat())}. "
        f"Found {len(issues)} issues across {len(analysis.get('files', {}))} files. "
        f"Overall score: {overall_score}/100."
    )

    # Assemble report
    report: Dict[str, Any] = {
        "meta": analysis.get("meta", {}),
        "summary": summary,
        "overall_score": overall_score,
        "issues": issues,
        "files": analysis.get("files", {}),
        "recommendations": recommendations,
    }

    # Add Markdown summary
    report["markdown"] = report_to_markdown(report, title="Code Quality Report")

    return report


def report_to_markdown(report: Dict[str, Any], title: str = "CQIA Report") -> str:
    """
    Convert report into a human-readable Markdown string.

    Args:
        report (Dict[str, Any]): Canonical report dict.

    Returns:
        str: Markdown representation of the report.
    """
    md_lines: List[str] = []
    md_lines.append("# Code Quality Report\n")
    md_lines.append(f"**Overall Score:** {report.get('overall_score', '?')}/100\n")

    # Top Issues Table
    md_lines.append("## Top Issues\n")
    md_lines.append("| ID | Severity | Location | Message |")
    md_lines.append("|----|----------|----------|---------|")
    top_issues = sorted(report.get("issues", []), key=lambda x: x["score"], reverse=True)[:5]
    for issue in top_issues:
        location = f"{issue.get('file')}:{issue.get('lineno')}" if issue.get("file") else "N/A"
        message = issue.get("message", "")
        md_lines.append(f"| {issue['id']} | {issue['severity']} | {location} | {message} |")

    # Recommendations
    md_lines.append("\n## Recommendations\n")
    for rec in report.get("recommendations", []):
        md_lines.append(f"- {rec}")

    return "\n".join(md_lines)
