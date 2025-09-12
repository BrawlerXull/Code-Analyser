from pathlib import Path
from typing import List, Dict

# Simple language detection by file extension
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
}

class FSIngestor:
    def __init__(self, root: Path):
        self.root = Path(root)

    def collect_files(self) -> List[Dict]:
        """
        Walk the directory and collect code files with basic language detection.
        Returns: list of dicts {path, lang, text}
        """
        results = []
        for file_path in self.root.rglob("*"):
            if not file_path.is_file():
                continue
            lang = self.detect_language(file_path.suffix)
            if not lang:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = ""
            results.append({
                "path": str(file_path),
                "lang": lang,
                "text": text
            })
        return results

    def detect_language(self, suffix: str) -> str:
        return LANGUAGE_MAP.get(suffix.lower())
