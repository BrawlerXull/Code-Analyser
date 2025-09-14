"""
QA Service for answering natural-language questions about analysis reports.

LLM Path:
---------
LLM/Gemini-based answers are enabled only when `config.use_llm` is True.
Gemini API is used instead of OpenAI. If LLM is disabled or AgentController unavailable,
a simple rule-based fallback is used.

Usage examples:
---------------
>>> from core.services.qa_service import answer_question
>>> report = {"overall_score": 75, "issues": [
...   {"id": "PY-SEC-001", "category": "security", "severity": "critical",
...    "file": "app/main.py", "lineno": 10, "message": "Use of eval()",
...    "suggested_fix": "Avoid eval(); use ast.literal_eval instead."}
... ], "summary": "1 security issue"}
>>> answer_question(report, "What are the most severe issues?")
{'answer': 'Top 1 issues:\\n- [PY-SEC-001] security (critical) in app/main.py: Use of eval()',
 'sources': ['app/main.py'],
 'confidence': 'high'}
"""

from typing import Dict, Any, List
import re
import json

from config.llm_config import load_llm_config

# Optional Gemini Agent
try:
    from core.agent.agent_controller import AgentController
except Exception:
    AgentController = None


def answer_question(report: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Answer a natural-language question about a report.

    Args:
        report: Dict containing report data (issues, overall_score, summary, etc.)
        question: Natural-language question string.

    Returns:
        dict with keys:
            - "answer": str
            - "sources": List[str] (filenames referenced)
            - "confidence": "low" | "medium" | "high"
    """
    # Load LLM/Gemini config
    cfg = load_llm_config()

    # Use AgentController if available and LLM enabled
    if cfg.use_llm and AgentController is not None:
        try:
            agent = AgentController(cfg)  # Gemini API usage internally
            # Attempt to map question to issue
            issue_id_match = re.search(r"(py|js)-\w+-\d+", question, flags=re.I)
            if issue_id_match:
                issue_id = issue_id_match.group(0).upper()
                resp = agent.explain_issue(report, issue_id)
            else:
                # Generic QA via agent.ask() with RAG+Gemini API
                resp = agent.ask(report, question)
            
            return {
                "answer": resp.get("answer", str(resp)),
                "sources": resp.get("sources", []),
                "confidence": resp.get("confidence", "medium"),
            }
        except Exception:
            # Fallback to rule-based if Gemini agent fails
            pass

    # Fallback: simple rule-based QA
    return _rule_based_qa(report, question)


def _rule_based_qa(report: Dict[str, Any], question: str) -> Dict[str, Any]:
    """
    Enhanced rule-based QA fallback.
    """
    q = question.lower()
    issues: List[Dict[str, Any]] = report.get("issues", [])
    sources: List[str] = []

    # Case 1: Top / highest / most severe
    if any(word in q for word in ["top", "highest", "most severe"]):
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "missing": 0}
        sorted_issues = sorted(
            issues,
            key=lambda x: (severity_order.get(x.get("severity", "low"), 0), x.get("id", "")),
            reverse=True,
        )
        top = sorted_issues[:3]
        if not top:
            return {"answer": "No issues found.", "sources": [], "confidence": "low"}
        answer_lines = ["Top {} issues:".format(len(top))]
        for issue in top:
            answer_lines.append(
                f"- [{issue.get('id')}] {issue.get('category')} ({issue.get('severity')}) "
                f"in {issue.get('file')}:{issue.get('lineno') or '?'}: {issue.get('message')}"
            )
            sources.append(issue.get("file", ""))
        return {"answer": "\n".join(answer_lines), "sources": sources, "confidence": "high"}

    # Case 2: Missing tests
    if any(word in q for word in ["missing tests", "tests missing", "no tests"]):
        missing = [i for i in issues if i.get("category") == "testing" and i.get("severity") == "missing"]
        if not missing:
            return {"answer": "No missing tests detected.", "sources": [], "confidence": "high"}
        answer_lines = [f"Missing tests detected in {len(missing)} location(s):"]
        for i in missing:
            sources.append(i.get("file", ""))
            answer_lines.append(f"- {i.get('file')} : {i.get('message')}")
        return {"answer": "\n".join(answer_lines), "sources": sources, "confidence": "high"}

    # Case 3: Specific filename mentioned
    file_match = re.search(r"([\w./-]+\.(?:py|js))", q)
    if file_match:
        filename = file_match.group(1)
        file_issues = [i for i in issues if i.get("file") and filename in i.get("file")]
        if not file_issues:
            return {"answer": f"No issues found for {filename}.", "sources": [filename], "confidence": "medium"}
        answer_lines = [f"Issues for {filename}:"]
        for issue in file_issues[:5]:
            answer_lines.append(
                f"- [{issue.get('id')}] {issue.get('severity')} {issue.get('category')}: {issue.get('message')}"
            )
        return {"answer": "\n".join(answer_lines), "sources": [filename], "confidence": "medium"}

    # Case 4: How to fix issue by id
    id_match = re.search(r"(py|js)-\w+-\d+", q, flags=re.I)
    if "how to fix" in q and id_match:
        issue_id = id_match.group(0).upper()
        issue = next((i for i in issues if i.get("id", "").upper() == issue_id), None)
        if not issue:
            return {"answer": f"Issue {issue_id} not found.", "sources": [], "confidence": "low"}
        return {
            "answer": f"Suggested fix for {issue_id}: {issue.get('suggested_fix', 'No fix available.')}",
            "sources": [issue.get("file", "")],
            "confidence": "high",
        }
    
    # Case 5: High complexity
    if any(word in q for word in ["high complexity", "complex functions", "complexity issues"]):
        high_complexity = [i for i in issues if i.get("category") == "complexity" and i.get("severity") == "high"]
        if not high_complexity:
            return {"answer": "No high complexity functions found.", "sources": [], "confidence": "high"}
        answer_lines = [f"High complexity functions ({len(high_complexity)} found):"]
        for i in high_complexity[:10]:  # limit to 10
            sources.append(i.get("file", ""))
            answer_lines.append(
                f"- {i.get('file')}:{i.get('lineno') or '?'} - {i.get('id')}: {i.get('message')}"
            )
        return {"answer": "\n".join(answer_lines), "sources": list(set(sources)), "confidence": "high"}
    
    # Case 6: Security issues
    if any(word in q for word in ["security", "vulnerability", "vulnerabilities", "security issues"]):
        security_issues = [i for i in issues if i.get("category") == "security"]
        if not security_issues:
            return {"answer": "No security issues found.", "sources": [], "confidence": "high"}
        answer_lines = [f"Security issues ({len(security_issues)} found):"]
        sec_sources = []
        for i in security_issues[:10]:  # limit to 10
            sec_sources.append(i.get("file", ""))
            answer_lines.append(
                f"- {i.get('file')}:{i.get('lineno') or '?'} - {i.get('id')}: {i.get('message')}"
            )
        return {"answer": "\n".join(answer_lines), "sources": list(set(sec_sources)), "confidence": "high"}


    # Default fallback: summarize report
    overall = report.get("overall_score", 0)
    summary = report.get("summary", "")
    return {
        "answer": f"Overall score: {overall}/100. Summary: {summary}",
        "sources": [],
        "confidence": "medium",
    }
