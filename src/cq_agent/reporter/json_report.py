import json
from pathlib import Path
from typing import Any

class JSONReporter:
    def write(self, data: Any, out: Path):
        """
        Write collected data to a JSON file.
        """
        report = {
            "meta": {
                "total_files": len(data),
            },
            "files": data
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
