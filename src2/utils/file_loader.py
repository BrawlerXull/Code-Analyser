from pathlib import Path
from typing import List


SUPPORTED_EXTENSIONS = {".py", ".js"}




class FileLoader:
    def load(self, path: str) -> List[Path]:
        p = Path(path)
        files = []
        if p.is_file():
            if p.suffix in SUPPORTED_EXTENSIONS:
                files.append(p)
                return files


            for child in p.rglob("*"):
                if child.is_file() and child.suffix in SUPPORTED_EXTENSIONS:
                    files.append(child)
                    return files