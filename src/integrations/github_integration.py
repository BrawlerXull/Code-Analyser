# src/integrations/github_integration.py
"""
GitHub Integration Module

Provides utilities to post analysis results as PR comments or check runs.

Usage:
------
>>> from integrations.github_integration import post_pr_comment, create_check_run, run_on_pr_and_report
>>> report = {"overall_score": 85, "issues": [{"id": "PY-SEC-001", "severity": "high", "file": "app.py"}]}
>>> post_pr_comment("my-org/my-repo", 42, "Analysis complete.", github_token="ghp_xxx")
>>> create_check_run("my-org/my-repo", head_sha="abc123", name="CQIA", status="completed", conclusion="success", output={"title":"CQIA Report","summary":"All good"})
>>> run_on_pr_and_report("my-org/my-repo", 42, report, github_token="ghp_xxx")
"""

import os
import json
import requests
from typing import Dict, Any, List

GITHUB_API_URL = "https://api.github.com"


def post_pr_comment(
    repo_full_name: str,
    pr_number: int,
    body: str,
    github_token: str = None
) -> Dict:
    """
    Post a comment to a GitHub Pull Request.

    Args:
        repo_full_name: "owner/repo" string.
        pr_number: PR number to comment on.
        body: Comment content (Markdown supported).
        github_token: Personal access token (optional, defaults to env GITHUB_TOKEN).

    Returns:
        JSON response from GitHub API.
    """
    token = github_token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GitHub token required via parameter or GITHUB_TOKEN env var.")

    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    payload = {"body": body}

    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to post PR comment: {resp.status_code}, {resp.text}")
    return resp.json()


def create_check_run(
    repo_full_name: str,
    head_sha: str,
    name: str,
    status: str,
    conclusion: str,
    output: Dict[str, Any],
    github_token: str = None
) -> Dict:
    """
    Create a GitHub Check Run on a commit.

    Args:
        repo_full_name: "owner/repo" string.
        head_sha: Commit SHA to attach check to.
        name: Name of the check run.
        status: "queued", "in_progress", "completed".
        conclusion: "success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required".
        output: Dict with 'title', 'summary', and optional 'annotations' list (max 50 per API limit).
        github_token: Personal access token (optional, defaults to env GITHUB_TOKEN).

    Returns:
        JSON response from GitHub API.
    """
    token = github_token or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GitHub token required via parameter or GITHUB_TOKEN env var.")

    url = f"{GITHUB_API_URL}/repos/{repo_full_name}/check-runs"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "name": name,
        "head_sha": head_sha,
        "status": status,
        "conclusion": conclusion if status == "completed" else None,
        "output": output
    }

    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create check run: {resp.status_code}, {resp.text}")
    return resp.json()


def run_on_pr_and_report(
    repo_full_name: str,
    pr_number: int,
    analysis_report: Dict[str, Any],
    github_token: str = None
):
    """
    Format top issues from analysis report and post to PR as comment and/or check run.

    Args:
        repo_full_name: "owner/repo"
        pr_number: Pull request number
        analysis_report: Report dict from CQIA
        github_token: GitHub personal access token

    Behavior:
        - Summarizes top 5 issues
        - Posts as PR comment
        - Optionally creates a check run
    """
    issues = analysis_report.get("issues", [])
    top_issues = sorted(issues, key=lambda x: x.get("score", 0), reverse=True)[:5]

    comment_lines: List[str] = [
        f"**CQIA Analysis Report**",
        f"Overall Score: {analysis_report.get('overall_score', '?')}/100",
        "",
        "**Top Issues:**"
    ]

    for i, issue in enumerate(top_issues, 1):
        loc = f"{issue.get('file', '?')}:{issue.get('lineno','?')}"
        comment_lines.append(
            f"{i}. [{issue.get('id')}] {issue.get('category')} ({issue.get('severity')}) at {loc} - {issue.get('message')}"
        )

    comment_body = "\n".join(comment_lines)

    # Post PR comment
    post_pr_comment(repo_full_name, pr_number, comment_body, github_token=github_token)

    # Optionally, create a check run with summary
    # In practice, fetch head_sha from PR API if not known; here we assume user supplies correct SHA in output
    head_sha = analysis_report.get("meta", {}).get("head_sha") or ""
    output = {
        "title": "CQIA Analysis Report",
        "summary": comment_body[:6000]  # GitHub limit for summary
    }
    if head_sha:
        create_check_run(
            repo_full_name,
            head_sha=head_sha,
            name="CQIA",
            status="completed",
            conclusion="neutral",
            output=output,
            github_token=github_token
        )


if __name__ == "__main__":
    # Example usage
    sample_report = {
        "overall_score": 88,
        "issues": [
            {"id": "PY-SEC-001", "category": "security", "severity": "high", "file": "app.py", "lineno": 10, "message": "Use of eval()"},
            {"id": "PY-COM-002", "category": "complexity", "severity": "medium", "file": "utils.py", "lineno": 22, "message": "Complex function"}
        ],
        "meta": {"head_sha": "abc123"}
    }
    repo = "my-org/my-repo"
    pr_num = 42
    token = os.environ.get("GITHUB_TOKEN")
    run_on_pr_and_report(repo, pr_num, sample_report, github_token=token)
    print("Posted report to PR successfully.")
