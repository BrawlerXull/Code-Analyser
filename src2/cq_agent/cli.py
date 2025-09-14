import typer
from pathlib import Path
from cq_agent.ingestion.fs_ingestor import FSIngestor
from cq_agent.reporter.json_report import JSONReporter
from cq_agent.reporter.md_report import MarkdownReporter
from cq_agent.analysis.aggregator import Aggregator
from cq_agent.analyzers.python_complexity import PythonComplexityAnalyzer
from cq_agent.analyzers.js_basic import JSBasicAnalyzer

app = typer.Typer(help="Code Quality Intelligence Agent CLI", no_args_is_help=True)

@app.command("analyze")
def analyze(
    path: Path = typer.Argument(..., help="Path to the codebase to analyze"),
    out: Path = typer.Option("cq_report.json", "--out", "-o", help="Output JSON file"),
    md: Path = typer.Option(None, "--md", help="Optional Markdown output file"),
):
    """Analyze a codebase and write reports."""
    ingestor = FSIngestor(root=path)
    files = ingestor.collect_files()

    analyzers = [PythonComplexityAnalyzer(), JSBasicAnalyzer()]
    agg = Aggregator(analyzers)
    report = agg.run(files)

    JSONReporter().write(report, out)
    typer.echo(f"[cq-agent] JSON report written to {out}")

    if md:
        MarkdownReporter().write(report, md)
        typer.echo(f"[cq-agent] Markdown report written to {md}")

def main():
    app()

if __name__ == "__main__":
    main()
