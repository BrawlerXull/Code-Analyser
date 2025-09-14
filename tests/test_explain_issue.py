# test_explain_issue.py
from core.agent.agent_controller import AgentController

# Sample report
report = {
    "overall_score": 85,
    "summary": "1 security issue, 1 missing test",
    "issues": [
        {
            "id": "PY-SEC-001",
            "category": "security",
            "severity": "critical",
            "file": "app/main.py",
            "lineno": 10,
            "message": "Use of eval()",
            "suggested_fix": "Avoid eval(); use ast.literal_eval instead."
        },
        {
            "id": "PY-TEST-002",
            "category": "testing",
            "severity": "missing",
            "file": "tests/test_main.py",
            "lineno": None,
            "message": "Missing unit test for main function",
            "suggested_fix": "Add unit tests"
        }
    ]
}

# Initialize agent
agent = AgentController()

# Test explain_issue
issue_id = "PY-TEST-002"
explanation = agent.explain_issue(report, issue_id)

print("Explanation output:")
print(explanation)
