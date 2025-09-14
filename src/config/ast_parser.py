# src/core/ast_parser.py
"""
Advanced AST Parser for Python and JavaScript

This module provides cross-file structure extraction, symbol resolution,
and call graph generation for Python and JavaScript repositories.

It uses Python's `ast` module for Python parsing and optionally Tree-sitter
for JS parsing. Falls back to regex heuristics if Tree-sitter is unavailable.
"""

import os
import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

try:
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


def build_python_symbol_table(path: str) -> Dict[str, Any]:
    """
    Walk a directory for .py files and build a symbol table with modules, functions, classes, and imports.

    Args:
        path: Root directory of Python repository.

    Returns:
        Dict[str, Any] with shape:
        {
            "modules": {
                "pkg.module": {
                    "functions": [{"name": str, "lineno": int, "args": [str], "snippet": str}],
                    "classes": [{"name": str, "lineno": int, "methods": [...] }],
                    "imports": [{"module": str, "names": [str]}],
                    "warnings": [str]
                }
            }
        }
    """
    repo_path = Path(path).resolve()
    symbol_table: Dict[str, Any] = {"modules": {}}

    for py_file in repo_path.rglob("*.py"):
        module_name = str(py_file.relative_to(repo_path)).replace(os.sep, ".").rstrip(".py")
        module_entry = {"functions": [], "classes": [], "imports": [], "warnings": []}

        try:
            with py_file.open("r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=str(py_file))
        except Exception as e:
            module_entry["warnings"].append(f"Failed to parse {py_file}: {e}")
            symbol_table["modules"][module_name] = module_entry
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                snippet = ast.get_source_segment(source, node)
                module_entry["functions"].append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "args": args,
                    "snippet": snippet[:100] if snippet else ""
                })
            elif isinstance(node, ast.ClassDef):
                methods = []
                for n in node.body:
                    if isinstance(n, ast.FunctionDef):
                        methods.append({"name": n.name, "lineno": n.lineno})
                module_entry["classes"].append({"name": node.name, "lineno": node.lineno, "methods": methods})
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in getattr(node, "names", [])]
                module_entry["imports"].append({"module": getattr(node, "module", None), "names": names})

        symbol_table["modules"][module_name] = module_entry

    return symbol_table


def resolve_crossrefs(symbol_table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze imports to link functions across modules.

    Args:
        symbol_table: Output from build_python_symbol_table

    Returns:
        Dict with call_graph edges:
        {
            "call_graph": [
                {"caller_file": str, "callee_module": str, "callee_name": str, "lineno": int}
            ]
        }
    """
    call_graph = []

    # Simple heuristic: check function calls inside each module
    for mod_name, mod_data in symbol_table.get("modules", {}).items():
        for func in mod_data.get("functions", []):
            snippet = func.get("snippet", "")
            # crude regex to find function calls: foo(...) or module.func(...)
            matches = re.findall(r"(\w+(?:\.\w+)*)\s*\(", snippet)
            for match in matches:
                if "." in match:
                    callee_module, callee_name = match.rsplit(".", 1)
                else:
                    callee_module, callee_name = mod_name, match
                call_graph.append({
                    "caller_file": mod_name,
                    "callee_module": callee_module,
                    "callee_name": callee_name,
                    "lineno": func.get("lineno")
                })

    return {"call_graph": call_graph}


def extract_js_structure(path: str) -> Dict[str, Any]:
    """
    Extract JS/TS module structure using Tree-sitter if available, else regex heuristics.

    Args:
        path: Root directory

    Returns:
        Dict[str, Any] similar to Python symbol table:
        {
            "modules": {
                "module_name": {
                    "functions": [...],
                    "classes": [...],
                    "imports": [...],
                    "warnings": [...]
                }
            }
        }
    """
    repo_path = Path(path).resolve()
    symbol_table: Dict[str, Any] = {"modules": {}}

    for js_file in repo_path.rglob("*.js"):
        module_name = str(js_file.relative_to(repo_path)).replace(os.sep, ".").rstrip(".js")
        module_entry = {"functions": [], "classes": [], "imports": [], "warnings": []}

        try:
            with js_file.open("r", encoding="utf-8") as f:
                source = f.read()
            if TREE_SITTER_AVAILABLE:
                # Placeholder for Tree-sitter logic
                # TODO: implement actual parsing
                pass
            else:
                # Regex-based heuristic
                for m in re.finditer(r"function\s+(\w+)\s*\(", source):
                    module_entry["functions"].append({"name": m.group(1), "lineno": source[:m.start()].count("\n")+1, "snippet": source[m.start():m.end()]})
                imports = re.findall(r"(?:import .* from ['\"](.*)['\"])|(?:require\(['\"](.*)['\"]\))", source)
                imports_flat = [i for t in imports for i in t if i]
                module_entry["imports"] = [{"module": i, "names": []} for i in imports_flat]
        except Exception as e:
            module_entry["warnings"].append(f"Failed to parse {js_file}: {e}")

        symbol_table["modules"][module_name] = module_entry

    return symbol_table


def generate_call_graph(symbol_table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a call graph mapping nodes to outgoing edges with counts.

    Args:
        symbol_table: Symbol table from Python or JS extraction.

    Returns:
        Dict[str, Any]:
        {
            "nodes": ["module.func", ...],
            "edges": [{"from": "module.func", "to": "module2.func", "count": int}]
        }
    """
    call_graph_edges: Dict[Tuple[str, str], int] = {}
    nodes: set = set()

    # Use Python call graph as base if exists
    cg = symbol_table.get("call_graph", [])
    for edge in cg:
        caller = f"{edge['caller_file']}.{edge['callee_name']}"
        callee = f"{edge['callee_module']}.{edge['callee_name']}"
        nodes.update([caller, callee])
        key = (caller, callee)
        call_graph_edges[key] = call_graph_edges.get(key, 0) + 1

    edges_list = [{"from": k[0], "to": k[1], "count": v} for k, v in call_graph_edges.items()]

    return {"nodes": list(nodes), "edges": edges_list}


if __name__ == "__main__":
    # Example usage
    python_symbols = build_python_symbol_table(".")
    print(json.dumps(python_symbols, indent=2))

    crossrefs = resolve_crossrefs(python_symbols)
    print(json.dumps(crossrefs, indent=2))

    js_symbols = extract_js_structure(".")
    print(json.dumps(js_symbols, indent=2))

    cg = generate_call_graph(crossrefs)
    print(json.dumps(cg, indent=2))
