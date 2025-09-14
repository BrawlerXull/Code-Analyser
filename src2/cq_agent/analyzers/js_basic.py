from typing import Dict, Any
from cq_agent.analyzers.base import Analyzer

class JSBasicAnalyzer(Analyzer):
    def analyze(self, file: Dict[str, Any]) -> Dict[str, Any]:
        if file["lang"] != "javascript":
            return {}

        tokens = file["text"].replace("\n", " ").split()
        return {
            "analyzer": self.name,
            "token_count": len(tokens),
        }
