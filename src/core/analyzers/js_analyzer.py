"""
js_analyzer.py - Lightweight JavaScript/TypeScript static analyzer (implemented in Python)

This module scans JavaScript/TypeScript files for simple code-quality signals:
- Suspicious patterns (eval, new Function, innerHTML, document.write)
- TODO/FIXME comments
- Simple duplication detection (normalized function bodies hashed)
- Missing tests detection (package.json test script or presence of test files)

The analyzer is defensive: it will use tree-sitter if available and a JS grammar
is accessible, but will gracefully fall back to robust regex-based heuristics
when tree-sitter or grammars are not present.

Return structure example:
{
  "language": "javascript",
  "files": {
    "src/app.js": {
      "functions": [
        {"name": "doThing", "lineno": 10}
      ],
      "todos": [{"lineno": 2, "text": "// TODO: fix this"}],
      "security_warnings": [
        {"type": "eval", "lineno": 42, "snippet": "eval(userInput)"}
      ],
      "duplication_hashes": ["ab12..."]
    }
  },
  "issues": [
    {
      "id": "JS-SEC-1a2b3c4d",
      "category": "security",
      "severity": "high",
      "file": "src/app.js",
      "lineno": 42,
      "message": "Use of eval detected.",
      "evidence": "eval(userInput)",
      "suggested_fix": "Avoid eval; use safer parsing or explicit APIs."
    }
  ],
  "summary": "Found 5 JS/TS files, 3 issues (2 security, 1 duplication) [tree-sitter: unavailable]"
}
"""

import os
import re
import hashlib
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Optional tree-sitter support
try:
    import tree_sitter
    from tree_sitter import Language, Parser  # type: ignore
except Exception:
    tree_sitter = None  # type: ignore

# File extensions to consider
JS_EXTS = {".js", ".jsx", ".mjs", ".ts", ".tsx"}

IGNORED_DIRS = {"node_modules", ".git", "venv", ".venv", "env"}


def _safe_read(path: Path) -> str:
    """Read file safely, ignoring encoding errors."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _hash_issue(file: str, lineno: Optional[int], category: str) -> str:
    """Generate a short deterministic issue id."""
    base = f"{file}:{lineno}:{category}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:8]


def _find_todos(source: str) -> List[Dict[str, Any]]:
    """Find TODO/FIXME in JS-style comments."""
    todos: List[Dict[str, Any]] = []
    for idx, line in enumerate(source.splitlines(), 1):
        if "TODO" in line or "FIXME" in line:
            todos.append({"lineno": idx, "text": line.strip()})
    return todos


# Regex patterns for suspicious constructs (fallback)
SUSPICIOUS_PATTERNS = {
    "eval": re.compile(r"\beval\s*\(", re.IGNORECASE),
    "new_function": re.compile(r"new\s+Function\s*\(", re.IGNORECASE),
    "innerHTML": re.compile(r"\.innerHTML\b", re.IGNORECASE),
    "document_write": re.compile(r"document\.write\s*\(", re.IGNORECASE),
}


# Simple function body regexes for duplication detection (best-effort)
FUNCTION_PATTERNS = [
    # function name(...) { ... }
    re.compile(r"function\s+([A-Za-z0-9_$]+)\s*\([^)]*\)\s*\{", re.MULTILINE),
    # const name = function(...) { ... } or let/var
    re.compile(r"(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*function\s*\([^)]*\)\s*\{", re.MULTILINE),
    # const name = (...) => { ... }
    re.compile(r"(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*\([^)]*\)\s*=>\s*\{", re.MULTILINE),
    # Arrow without parens: x => { ... }
    re.compile(r"(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*[A-Za-z0-9_$]+\s*=>\s*\{", re.MULTILINE),
]


def _extract_functions_regex(source: str) -> List[Dict[str, Any]]:
    """
    Best-effort extraction of function names and approximate lineno using regex.
    Returns list of {"name": str, "lineno": int, "body": str}.
    """
    functions: List[Dict[str, Any]] = []
    lines = source.splitlines()
    for patt in FUNCTION_PATTERNS:
        for m in patt.finditer(source):
            name = m.group(1)
            # estimate lineno by counting newlines before match
            lineno = source[: m.start()].count("\n") + 1
            # naive body extraction: find the next matching closing brace at same nesting
            start = m.end() - 1  # position of '{'
            brace = 0
            end_idx = None
            for i in range(start, len(source)):
                ch = source[i]
                if ch == "{":
                    brace += 1
                elif ch == "}":
                    brace -= 1
                    if brace == 0:
                        end_idx = i + 1
                        break
            body = source[m.start(): end_idx] if end_idx else source[m.start(): m.end() + 200]
            functions.append({"name": name, "lineno": lineno, "body": body})
    # deduplicate by (name, lineno)
    seen = set()
    unique = []
    for f in functions:
        key = (f["name"], f["lineno"])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def _normalize_code_for_hash(code: str) -> str:
    """Normalize code by removing whitespace & comments for duplication hashing."""
    # remove JS single-line and block comments
    code = re.sub(r"//.*?$", "", code, flags=re.MULTILINE)
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    # collapse whitespace
    code = re.sub(r"\s+", " ", code).strip()
    return code


def _detect_suspicious_regex(source: str) -> List[Dict[str, Any]]:
    """Find suspicious constructs via regex and return list of warnings."""
    warnings: List[Dict[str, Any]] = []
    for name, patt in SUSPICIOUS_PATTERNS.items():
        for m in patt.finditer(source):
            lineno = source[: m.start()].count("\n") + 1
            snippet = source[m.start() : m.end() + 80].splitlines()[0][:200]
            warnings.append({"type": name, "lineno": lineno, "snippet": snippet})
    return warnings


def analyze_js_repo(path: str) -> Dict[str, Any]:
    """
    Analyze JavaScript/TypeScript files in a repository.

    Args:
        path (str): Path to repository root.

    Returns:
        Dict[str, Any]: Analysis report with keys: language, files, issues, summary.

    Notes:
        - Uses tree-sitter if available and a JS grammar has been built and is loadable.
        - Otherwise falls back to regex-based heuristics which are conservative but robust.
    """
    repo_path = Path(path).resolve()
    files_data: Dict[str, Any] = {}
    issues: List[Dict[str, Any]] = []
    file_count = 0
    tree_sitter_available = False

    # Quick attempt to see if tree-sitter JS parser is usable.
    # We do not attempt to build a grammar here; user is responsible for having a compiled .so if desired.
    if tree_sitter is not None:
        try:
            parser = Parser()
            # Attempt to load a language if environment variable points to a compiled language
            # COMMON env var: TS_LANG_SO pointing to an aggregate .so with javascript
            ts_so = os.environ.get("TS_LANG_SO")
            if ts_so and Path(ts_so).exists():
                JS_LANG = Language(ts_so, "javascript")
                parser.set_language(JS_LANG)
                tree_sitter_available = True
        except Exception:
            tree_sitter_available = False

    # Walk directory
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext in JS_EXTS:
                file_count += 1
                fpath = Path(root) / fname
                rel_path = str(fpath.relative_to(repo_path))
                source = _safe_read(fpath)

                file_report: Dict[str, Any] = {
                    "functions": [],
                    "todos": [],
                    "security_warnings": [],
                    "duplication_hashes": []
                }

                # TODOs
                file_report["todos"] = _find_todos(source)
                for todo in file_report["todos"]:
                    issues.append({
                        "id": "JS-DOC-" + _hash_issue(rel_path, todo["lineno"], "todo"),
                        "category": "documentation",
                        "severity": "low",
                        "file": rel_path,
                        "lineno": todo["lineno"],
                        "message": "TODO/FIXME comment found.",
                        "evidence": todo["text"],
                        "suggested_fix": "Resolve or remove TODO/FIXME."
                    })

                # Parse with tree-sitter if available
                susp_warnings: List[Dict[str, Any]] = []
                functions_extracted: List[Dict[str, Any]] = []

                if tree_sitter_available:
                    # Best-effort: parse and extract function names and suspicious calls
                    try:
                        tree = parser.parse(bytes(source, "utf8"))
                        root_node = tree.root_node

                        # Walk nodes looking for call_expression with identifier named eval, document.write etc.
                        # Since grammars vary, we use node.type checks conservatively.
                        to_visit = [root_node]
                        while to_visit:
                            node = to_visit.pop()
                            # detect call expressions with identifiers
                            if node.type == "call_expression" or node.type == "call":
                                # convert node to source snippet
                                snippet = source[node.start_byte: node.end_byte].strip()[:200]
                                # attempt to get function identifier text
                                func_text = source[node.child_by_field_name("function").start_byte: node.child_by_field_name("function").end_byte] if node.child_by_field_name("function") else ""
                                if "eval" in func_text:
                                    ln = source[: node.start_byte].count("\n") + 1
                                    susp_warnings.append({"type": "eval", "lineno": ln, "snippet": snippet})
                                elif "document.write" in snippet or ".innerHTML" in snippet:
                                    ln = source[: node.start_byte].count("\n") + 1
                                    susp_warnings.append({"type": "dom-xss", "lineno": ln, "snippet": snippet})
                                elif "Function" in func_text and "new" in snippet:
                                    ln = source[: node.start_byte].count("\n") + 1
                                    susp_warnings.append({"type": "new_function", "lineno": ln, "snippet": snippet})
                            # detect function declarations
                            if node.type in {"function_declaration", "method_definition", "arrow_function", "function"}:
                                # try to locate a name
                                name = None
                                # different grammars expose names differently; try common child fields
                                id_node = node.child_by_field_name("name") or node.child_by_field_name("identifier")
                                if id_node:
                                    name = source[id_node.start_byte: id_node.end_byte]
                                else:
                                    # fallback: find nearest identifier child
                                    for c in node.children:
                                        if c.type == "identifier":
                                            name = source[c.start_byte: c.end_byte]
                                            break
                                lineno = source[: node.start_byte].count("\n") + 1
                                # extract body snippet (limited)
                                body = source[node.start_byte: node.end_byte][:1000]
                                functions_extracted.append({"name": name or "<anonymous>", "lineno": lineno, "body": body})
                            for c in node.children:
                                to_visit.append(c)
                    except Exception:
                        # if tree-sitter fails for this file, fall back to regex
                        functions_extracted = _extract_functions_regex(source)
                        susp_warnings = _detect_suspicious_regex(source)
                else:
                    # tree-sitter not available: fall back to regex heuristics
                    functions_extracted = _extract_functions_regex(source)
                    susp_warnings = _detect_suspicious_regex(source)

                # Record functions
                for fn in functions_extracted:
                    file_report["functions"].append({"name": fn.get("name"), "lineno": fn.get("lineno")})

                # Security warnings
                for w in susp_warnings:
                    file_report["security_warnings"].append(w)
                    issues.append({
                        "id": "JS-SEC-" + _hash_issue(rel_path, w.get("lineno"), w.get("type")),
                        "category": "security",
                        "severity": "high" if w.get("type") in {"eval", "new_function", "dom-xss"} else "medium",
                        "file": rel_path,
                        "lineno": w.get("lineno"),
                        "message": f"Suspicious construct '{w.get('type')}' detected.",
                        "evidence": w.get("snippet"),
                        "suggested_fix": "Avoid dynamic code execution and unsafe DOM sinks; sanitize inputs and use safe APIs."
                    })

                # Duplication detection via normalized function bodies
                hashes = []
                for fn in functions_extracted:
                    body = fn.get("body", "")
                    norm = _normalize_code_for_hash(body)
                    if norm:
                        h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
                        hashes.append(h)
                file_report["duplication_hashes"] = hashes

                # If duplicate hash appears across files, we will mark duplication issues after scanning all files
                files_data[rel_path] = file_report

    # After scanning files, detect duplication across files
    all_hash_to_locations: Dict[str, List[str]] = {}
    for fpath, frep in files_data.items():
        for h in frep.get("duplication_hashes", []):
            all_hash_to_locations.setdefault(h, []).append(fpath)

    for h, locations in all_hash_to_locations.items():
        if len(locations) > 1:
            # create one issue per duplicated hash
            example_file = locations[0]
            issues.append({
                "id": "JS-DUP-" + _hash_issue(example_file, 0, "duplication"),
                "category": "duplication",
                "severity": "medium",
                "file": example_file,
                "lineno": None,
                "message": f"Code duplication detected across {len(locations)} files.",
                "evidence": json.dumps(locations),
                "suggested_fix": "Refactor duplicated code into shared modules or functions."
            })

    # Testing gap detection
    has_tests = False
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(_safe_read(pkg_json))
            scripts = pkg.get("scripts") or {}
            if "test" in scripts:
                has_tests = True
        except Exception:
            pass

    # also check for test files or __tests__ directories
    for root, dirs, files in os.walk(repo_path):
        if "__tests__" in dirs:
            has_tests = True
            break
        for fname in files:
            if fname.endswith((".test.js", ".spec.js", ".test.ts", ".spec.ts")):
                has_tests = True
                break
        if has_tests:
            break

    if not has_tests:
        issues.append({
            "id": "JS-TEST-" + _hash_issue(str(repo_path), 0, "testing"),
            "category": "testing",
            "severity": "missing",
            "file": str(repo_path),
            "lineno": None,
            "message": "No tests detected (no package.json test script or test files).",
            "evidence": "No tests found",
            "suggested_fix": "Add unit tests and a test script to package.json."
        })

    # Build summary
    summary_parts = [
        f"Found {file_count} JS/TS files",
        f"{len(issues)} issues"
    ]
    if tree_sitter is None:
        summary_parts.append("[Note: tree-sitter unavailable, using regex heuristics]")
    else:
        summary_parts.append("[Note: tree-sitter present]" if tree_sitter_available else "[Note: tree-sitter present but JS grammar not loaded]")

    summary = ", ".join(summary_parts)

    return {
        "language": "javascript",
        "files": files_data,
        "issues": issues,
        "summary": summary
    }
