from typing import List, Dict, Any

class Aggregator:
    def __init__(self, analyzers: List[Any]):
        self.analyzers = analyzers

    def run(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for f in files:
            file_result = {"path": f["path"], "lang": f["lang"], "analysis": []}
            for analyzer in self.analyzers:
                res = analyzer.analyze(f)
                if res:
                    file_result["analysis"].append(res)
            results.append(file_result)

        meta = {
            "total_files": len(files),
            "issues": sum(len(r["analysis"]) for r in results),
            "severity": "HIGH" if len(results) > 10 else "LOW",
        }

        return {"meta": meta, "results": results}
