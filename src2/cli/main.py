import typer
from pathlib import Path
from analyzer.python_analyzer import PythonAnalyzer
from analyzer.js_analyzer import JSAnalyzer
from utils.file_loader import FileLoader
from reports.report_generator import ReportGenerator


app = typer.Typer()


SUPPORTED_LANGS = {
".py": PythonAnalyzer,
".js": JSAnalyzer,
}




@app.command()
def analyze(path: str):
    """Analyze a local path (file or directory) and produce reports."""
    p = Path(path)
    if not p.exists():
        typer.echo(f"Path does not exist: {path}")
        raise typer.Exit(code=1)


loader = FileLoader()
files = loader.load(path)
if not files:
    typer.echo("No supported source files found (.py, .js)")
    raise typer.Exit(code=0)


# Group files by extension
results = {
"summary": {},
"issues": [],
}


for ext, analyzer_cls in SUPPORTED_LANGS.items():
    ext_files = [f for f in files if f.suffix == ext]
    if not ext_files:
        continue
    analyzer = analyzer_cls()
    for file_path in ext_files:
        text = file_path.read_text(encoding="utf-8")
        file_issues = analyzer.analyze_file(str(file_path), text)
        results["issues"].extend(file_issues)


generator = ReportGenerator()
out_paths = generator.generate(results)


typer.echo("Analysis complete.")
typer.echo(f"Reports written: {out_paths}")




if __name__ == "__main__":
    app()