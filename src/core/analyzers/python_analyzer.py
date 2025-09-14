"""
python_analyzer.py - Analyzer for Python source files.

Scans Python repositories for code quality issues:
parsing errors, cyclomatic complexity, security risks, duplications, TODOs, and missing tests.

All issues are returned with proper fields for manager.py and QA service.
"""

import os
import ast
import hashlib
from pathlib import Path
from typing import Dict, Any, List

try:
    from radon.complexity import cc_visit
except ImportError:
    cc_visit = None  # handle missing radon gracefully

IGNORED_DIRS = {"venv", ".venv", "env", "node_modules", ".git"}


def _hash_issue(file: str, lineno: int, category: str) -> str:
    """Generate deterministic unique issue ID."""
    base = f"{file}:{lineno}:{category}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]


def _safe_read(path: Path) -> str:
    """Read file safely, ignoring encoding errors."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _find_todos(source: str) -> List[Dict[str, Any]]:
    """Find TODO/FIXME comments."""
    todos = []
    for idx, line in enumerate(source.splitlines(), 1):
        if "TODO" in line or "FIXME" in line:
            todos.append({"lineno": idx, "text": line.strip()})
    return todos


def _approx_complexity(source: str) -> int:
    """Approximate cyclomatic complexity without radon."""
    keywords = ["if", "for", "while", "and", "or"]
    return sum(source.count(k) for k in keywords) + 1


def _detect_security_issues(tree: ast.AST, source: str, rel_path: str) -> List[Dict[str, Any]]:
    """Detect security-sensitive patterns in AST."""
    issues = []

    class SecurityVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            snippet = ast.get_source_segment(source, node) or func_name

            if func_name in {"eval", "exec"}:
                issues.append({
                    "id": "PY-SEC-" + _hash_issue(rel_path, node.lineno, func_name),
                    "category": "security",
                    "severity": "high",
                    "file": rel_path,
                    "lineno": node.lineno,
                    "message": f"Use of dangerous function '{func_name}'.",
                    "evidence": snippet,
                    "suggested_fix": "Avoid using eval/exec; consider safer alternatives."
                })
            elif func_name == "literal_eval":
                issues.append({
                    "id": "PY-SEC-" + _hash_issue(rel_path, node.lineno, func_name),
                    "category": "security",
                    "severity": "medium",
                    "file": rel_path,
                    "lineno": node.lineno,
                    "message": "literal_eval may be unsafe on untrusted input.",
                    "evidence": snippet,
                    "suggested_fix": "Validate inputs before using literal_eval."
                })
            elif func_name in {"system"}:
                issues.append({
                    "id": "PY-SEC-" + _hash_issue(rel_path, node.lineno, func_name),
                    "category": "security",
                    "severity": "high",
                    "file": rel_path,
                    "lineno": node.lineno,
                    "message": "os.system call detected.",
                    "evidence": snippet,
                    "suggested_fix": "Use subprocess with safe arguments instead of os.system."
                })
            self.generic_visit(node)

    SecurityVisitor().visit(tree)
    return issues


def analyze_python_repo(path: str) -> Dict[str, Any]:
    repo_path = Path(path).resolve()
    files_data: Dict[str, Any] = {}
    issues: List[Dict[str, Any]] = []
    file_count = 0

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            if fname.endswith(".py"):
                file_count += 1
                fpath = Path(root) / fname
                rel_path = str(fpath.relative_to(repo_path))
                source = _safe_read(fpath)

                file_report = {
                    "functions": [],
                    "classes": [],
                    "todos": [],
                    "security_warnings": [],
                    "duplication_hashes": []
                }

                # Parse AST
                try:
                    tree = ast.parse(source)
                except Exception as e:
                    issues.append({
                        "id": "PY-PARSE-" + _hash_issue(rel_path, 0, "parsing"),
                        "category": "parsing",
                        "severity": "medium",
                        "file": rel_path,
                        "lineno": None,
                        "message": f"Failed to parse Python file: {e}",
                        "evidence": source[:200],
                        "suggested_fix": "Ensure valid Python syntax."
                    })
                    files_data[rel_path] = file_report
                    continue

                # Functions & Classes
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        func_source = ast.get_source_segment(source, node) or ""
                        cc_val = (_approx_complexity(func_source)
                                  if not cc_visit else cc_visit(func_source)[0].complexity)

                        file_report["functions"].append({
                            "name": node.name,
                            "lineno": node.lineno,
                            "arg_count": len(node.args.args),
                            "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                            "cc": cc_val
                        })

                        # High complexity
                        if cc_val > 10:
                            issues.append({
                                "id": "PY-CPLX-" + _hash_issue(rel_path, node.lineno, "complexity"),
                                "category": "complexity",
                                "severity": "high",
                                "file": rel_path,
                                "lineno": node.lineno,
                                "message": f"Function '{node.name}' has high complexity (cc={cc_val}).",
                                "evidence": func_source[:200],
                                "suggested_fix": "Refactor function to reduce complexity."
                            })

                        # Duplication hash
                        norm_src = "".join(line.strip() for line in func_source.splitlines() if not line.strip().startswith("#"))
                        func_hash = hashlib.sha256(norm_src.encode("utf-8")).hexdigest()
                        file_report["duplication_hashes"].append(func_hash)

                    elif isinstance(node, ast.ClassDef):
                        file_report["classes"].append({
                            "name": node.name,
                            "lineno": node.lineno
                        })

                # TODOs
                file_report["todos"] = _find_todos(source)
                for todo in file_report["todos"]:
                    issues.append({
                        "id": "PY-TODO-" + _hash_issue(rel_path, todo["lineno"], "todo"),
                        "category": "documentation",
                        "severity": "low",
                        "file": rel_path,
                        "lineno": todo["lineno"],
                        "message": "TODO/FIXME comment found.",
                        "evidence": todo["text"],
                        "suggested_fix": "Resolve or remove TODO/FIXME."
                    })

                # Security
                sec_issues = _detect_security_issues(tree, source, rel_path)
                file_report["security_warnings"] = sec_issues
                issues.extend(sec_issues)

                files_data[rel_path] = file_report

    # Testing gaps
    packages = [p for p in repo_path.iterdir() if p.is_dir() and (p / "__init__.py").exists()]
    has_tests = (repo_path / "tests").exists()
    if not has_tests and packages:
        for pkg in packages:
            issues.append({
                "id": "PY-TEST-" + _hash_issue(str(pkg), 0, "testing"),
                "category": "testing",
                "severity": "missing",
                "file": str(pkg),
                "lineno": None,
                "message": f"Package '{pkg.name}' has no tests directory.",
                "evidence": "Missing tests/ directory.",
                "suggested_fix": "Add a tests/ folder with unit tests."
            })

    summary = (
        f"Found {file_count} Python files, {len(issues)} issues "
        f"({sum(1 for i in issues if i['category']=='parsing')} parsing errors, "
        f"{sum(1 for i in issues if i['category']=='complexity')} complexity, "
        f"{sum(1 for i in issues if i['category']=='security')} security, "
        f"{sum(1 for i in issues if i['category']=='duplication')} duplications, "
        f"{sum(1 for i in issues if i['category']=='testing')} testing gaps)"
    )

    return {
        "language": "python",
        "files": files_data,
        "issues": issues,
        "summary": summary
    }
