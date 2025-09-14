# src/core/dep_graph.py
"""
Dependency Graph Generator

Generates a graph of module/file dependencies and identifies hotspots
based on import usage and cross-file references. Returns a JSON-serializable
structure for visualization or analysis.

Example usage:
---------------
>>> from core.dep_graph import build_dep_graph
>>> graph = build_dep_graph("/path/to/repo")
>>> graph["nodes"][:3]
[{"id":"app.main","label":"app.main","hotness":5}, ...]
"""

from typing import Dict, Any, List

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from config.ast_parser import build_python_symbol_table, extract_js_structure, resolve_crossrefs


def build_dep_graph(path: str) -> Dict[str, Any]:
    """
    Build a dependency graph for a repository.

    Args:
        path: Path to the root of the repository.

    Returns:
        Dict containing:
            - nodes: list of {"id":module/file,"label":module/file,"hotness":int}
            - edges: list of {"source":src,"target":dst,"weight":int}
            - hotspots: top 5 nodes with highest connectivity or edge weights
    """
    py_symbols = build_python_symbol_table(path)
    js_symbols = extract_js_structure(path)
    symbols = {"python": py_symbols, "javascript": js_symbols}

    # Resolve cross-file references
    crossrefs = resolve_crossrefs(py_symbols)

    # Build edge list: (caller_module, callee_module, count)
    edge_weights: Dict[tuple, int] = {}
    for ref in crossrefs.get("call_graph", []):
        src = ref.get("caller_file")
        dst = ref.get("callee_module")
        if not src or not dst:
            continue
        key = (src, dst)
        edge_weights[key] = edge_weights.get(key, 0) + 1

    nodes_set = set()
    for src, dst in edge_weights.keys():
        nodes_set.add(src)
        nodes_set.add(dst)

    # Compute hotness per node (sum of incoming + outgoing edge weights)
    node_hotness: Dict[str, int] = {node: 0 for node in nodes_set}
    for (src, dst), w in edge_weights.items():
        node_hotness[src] += w
        node_hotness[dst] += w

    # Prepare nodes and edges lists
    nodes = [{"id":n, "label":n, "hotness":node_hotness[n]} for n in nodes_set]
    edges = [{"source":src, "target":dst, "weight":w} for (src, dst), w in edge_weights.items()]

    # Detect hotspots: top 5 nodes by hotness
    hotspots = sorted(
        [{"id":n, "score":node_hotness[n]} for n in node_hotness],
        key=lambda x: x["score"], reverse=True
    )[:5]

    # Optional networkx graph (if installed)
    if NETWORKX_AVAILABLE:
        G = nx.DiGraph()
        for node in nodes:
            G.add_node(node["id"], hotness=node["hotness"])
        for edge in edges:
            G.add_edge(edge["source"], edge["target"], weight=edge["weight"])
        # Could optionally compute additional centrality metrics here
    else:
        # Fallback: simple dict graph already prepared
        pass

    return {
        "nodes": nodes,
        "edges": edges,
        "hotspots": hotspots,
        "note": "NetworkX not installed" if not NETWORKX_AVAILABLE else "Graph built with NetworkX"
    }


if __name__ == "__main__":
    # Example usage
    import pprint
    graph = build_dep_graph(".")
    pprint.pprint(graph)
