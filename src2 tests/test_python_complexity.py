# tests/test_python_complexity.py
from cq_agent.analyzers.python_complexity import PythonComplexityAnalyzer

def test_simple_function():
    code = "def foo():\n    return 42\n"
    file = {"lang": "python", "text": code, "path": "foo.py"}
    res = PythonComplexityAnalyzer().analyze(file)
    assert res["functions"] == 1
    assert res["complexity"] > 0
