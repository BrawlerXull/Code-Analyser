from pathlib import Path
from typing import Any

class MarkdownReporter:
    def write(self, data: Any, out: Path):
        lines = ["# Code Quality Report", ""]
        lines.append(f"**Total files:** {data['meta']['total_files']}")
        lines.append(f"**Issues found:** {data['meta']['issues']}")
        lines.append(f"**Severity:** {data['meta']['severity']}")
        lines.append("")

        for f in data["results"]:
            lines.append(f"## {f['path']} ({f['lang']})")
            if not f["analysis"]:
                lines.append("- No issues found")
            for a in f["analysis"]:
                parts = [f"{k}: {v}" for k, v in a.items()]
                lines.append("- " + ", ".join(parts))
            lines.append("")

        out.write_text("\n".join(lines), encoding="utf-8")
