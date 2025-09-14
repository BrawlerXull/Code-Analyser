import json
from pathlib import Path
from typing import Any

class JSONReporter:
    def write(self, data: Any, out: Path):
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
