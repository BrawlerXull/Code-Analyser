"""
manager.py - Repository analysis orchestrator

This module coordinates analysis of a repository across multiple languages
(Python, JavaScript, etc.) and aggregates results into a single report.
"""

import os
import datetime
from pathlib import Path
from typing import List, Dict, Any

from core.analyzers.python_analyzer import analyze_python_repo
from core.analyzers.js_analyzer import analyze_js_repo
from core import severity

# Optional import for LLM config (if needed elsewhere)
try:
    from config.llm_config import load_llm_config
except ImportError:
    load_llm_config = None


def analyze_repo(
    path: str,
    languages: List[str] = None,
    index_for_rag: bool = False,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Analyze a code repository for quality issues across multiple languages.

    Args:
        path (str): Path to a file or directory containing source code.
        languages (List[str], optional): List of language codes to analyze.
            Defaults to ["py", "js"].
        index_for_rag (bool): If True, build vector store index for RAG.
        use_llm (bool): If True, enable LLM-enhanced analysis.

    Returns:
        Dict[str, Any]: Aggregated analysis results with keys:
            meta, summary, overall_score, languages, issues, files
    """
    if languages is None:
        languages = ["py", "js"]

    repo_path = Path(path).resolve()
    if not repo_path.exists():
        raise FileNotFoundError(f"Path does not exist: {repo_path}")
    if repo_path.is_file():
        repo_path = repo_path.parent

    results: Dict[str, Any] = {
        "meta": {},
        "summary": "",
        "overall_score": 100,
        "languages": [],
        "issues": [],
        "files": {}
    }

    issues: List[Dict[str, Any]] = []
    files: Dict[str, Any] = {}
    languages_used: List[str] = []

    # Run analyzers per language
    for lang in languages:
        if lang == "py":
            py_result = analyze_python_repo(str(repo_path))
            if py_result:
                issues.extend(py_result.get("issues", []))
                files.update(py_result.get("files", {}))
                languages_used.append("py")
        elif lang == "js":
            js_result = analyze_js_repo(str(repo_path))
            if js_result:
                issues.extend(js_result.get("issues", []))
                files.update(js_result.get("files", {}))
                languages_used.append("js")
        else:
            issues.append({
                "id": f"unknown-{lang}",
                "category": "warning",
                "message": f"Language '{lang}' not supported.",
                "severity": "low"
            })

    # Deduplicate issues by id
    for i, issue in enumerate(issues):
        if "id" not in issue or not issue["id"]:
            issue["id"] = f"ISSUE-{i+1}"

    unique_issues = {issue["id"]: issue for issue in issues}
    issues = list(unique_issues.values())

    print("Aggregated issues:")
    for issue in issues:
        print(issue)


    # Compute file hotness map
    file_hotness_map = {}
    for issue in issues:
        file_name = issue.get("file")
        if file_name:
            file_hotness_map[file_name] = file_hotness_map.get(file_name, 0) + 1

    severity.enrich_issues_with_scores(issues, file_hotness_map)


    # Compute overall score
    overall_score = severity.compute_overall_score(issues, repo_size=len(files))


    # Assemble summary string
    sec_high = sum(1 for i in issues if i.get("category") == "security" and i.get("severity") == "high")
    sec_med = sum(1 for i in issues if i.get("category") == "security" and i.get("severity") == "medium")
    complexity_high = sum(1 for i in issues if i.get("category") == "complexity" and i.get("severity") == "high")
    dup_count = sum(1 for i in issues if i.get("category") == "duplication")
    missing_tests = sum(1 for i in issues if i.get("category") == "testing" and i.get("severity") == "missing")

    summary = (
        f"Security issues: {sec_high + sec_med} "
        f"(high: {sec_high}, medium: {sec_med}), "
        f"Complexity issues: {complexity_high}, "
        f"Duplications: {dup_count}, "
        f"Missing tests: {missing_tests}"
    )

    # Fill meta
    results["meta"] = {
        "path": str(repo_path),
        "analyzed_at": datetime.datetime.utcnow().isoformat()
    }
    results["summary"] = summary
    results["overall_score"] = overall_score
    results["languages"] = languages_used
    results["issues"] = issues
    results["files"] = files

    # Optional RAG indexing
    if index_for_rag and use_llm:
        try:
            from core.rag.retriever import index_repo
            try:
                index_repo(str(repo_path), vector_store=None)  # Best-effort indexing
                results["meta"]["rag_indexed"] = True
            except Exception as e:
                results["meta"]["rag_indexed"] = False
                results["meta"]["rag_warning"] = f"Indexing failed: {e}"
        except ImportError:
            results["meta"]["rag_indexed"] = False
            results["meta"]["rag_warning"] = "core.rag.retriever.index_repo not available."

    return results
