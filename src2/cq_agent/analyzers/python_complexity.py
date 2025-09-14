import ast
from typing import Dict, Any
from cq_agent.analyzers.base import Analyzer

class PythonComplexityAnalyzer(Analyzer):
    def analyze(self, file: Dict[str, Any]) -> Dict[str, Any]:
        if file["lang"] != "python":
            return {}

        try:
            tree = ast.parse(file["text"])
        except SyntaxError:
            return {"analyzer": self.name, "error": "Syntax error"}

        func_count = 0
        class_count = 0
        complexity_score = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_count += 1
                complexity_score += 1 + len(node.body)
            elif isinstance(node, ast.ClassDef):
                class_count += 1

        return {
            "analyzer": self.name,
            "functions": func_count,
            "classes": class_count,
            "complexity": complexity_score,
        }
