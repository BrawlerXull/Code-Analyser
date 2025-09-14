# src/core/analyzers/python_analyzer.py
"""
Python Analyzer Module

Analyzes a Python repository:
1. Detects all functions
2. Detects control flow (optional)
3. Detects TODO comments

Returns a canonical report compatible with tests.
"""

import os
import ast
from typing import Dict, Any, List


def analyze_python_repo(repo_path: str) -> Dict[str, Any]:
    """
    Analyze Python files in a repository.

    Args:
        repo_path (str): Path to Python repository

    Returns:
        Dict[str, Any]: Report with functions, files, and TODOs
    """
    report: Dict[str, Any] = {
        "language": "python",
        "files": {},
        "functions": []
    }

    # Iterate over Python files
    for root, dirs, files in os.walk(repo_path):
        for f in files:
            if f.endswith(".py"):
                file_path = os.path.join(root, f)
                with open(file_path, "r", encoding="utf-8") as fp:
                    source = fp.read()

                file_report: Dict[str, Any] = {
                    "functions": [],
                    "todos": []
                }

                # Parse functions using AST
                try:
                    tree = ast.parse(source, filename=f)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            fn_info = {
                                "name": node.name,
                                "lineno": node.lineno,
                                "args": [arg.arg for arg in node.args.args]
                            }
                            file_report["functions"].append(fn_info)
                            report["functions"].append({
                                "name": node.name,
                                "file": f,
                                "lineno": node.lineno
                            })
                except Exception as e:
                    print(f"Warning: Failed to parse {f}: {e}")

                # Extract TODO comments
                todos = []
                for lineno, line in enumerate(source.splitlines(), start=1):
                    if "# TODO" in line:
                        todos.append(line.strip())
                file_report["todos"] = todos

                # Add file report
                report["files"][f] = file_report

    return report
