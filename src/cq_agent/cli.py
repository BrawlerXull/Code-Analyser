# src/cq_agent/cli.py

import typer
from pathlib import Path
from cq_agent.ingestion.fs_ingestor import FSIngestor
from cq_agent.reporter.json_report import JSONReporter

app = typer.Typer(
    help="Code Quality Intelligence Agent CLI",
    no_args_is_help=True
)

@app.callback(invoke_without_command=False)
def _callback():
    """
    Internal callback to force usage of subcommand names.
    """
    # This function exists only to force Typer into multi-command mode
    pass

def run_analysis(path: Path, out: Path):
    ingestor = FSIngestor(root=path)
    files = ingestor.collect_files()
    JSONReporter().write(files, out)
    typer.echo(f"[cq-agent] Report written to {out}")

@app.command("analyze")
def analyze(
    path: Path = typer.Argument(..., help="Path to the codebase to analyze"),
    out: Path = typer.Option("cq_report.json", "--out", "-o", help="Output JSON file"),
):
    """Analyze a codebase and write a JSON report."""
    run_analysis(path, out)

def main():
    app()

if __name__ == "__main__":
    main()
