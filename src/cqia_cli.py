"""
cqia_cli.py - Command Line Interface for Code Quality Intelligence Agent

This module provides a CLI for analyzing code repositories and interacting
with generated reports.

Usage Examples:
---------------
# Analyze a local repository (Python + JS) and save report
$ python -m src.cqia_cli analyze ./my-repo --languages py,js --out ./output

# Ask a question about a generated report
$ python -m src.cqia_cli qa 1 "What are the top security issues?"
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import List

import click

from core.analyzers.manager import analyze_repo
from core.storage import save_report, get_report_by_id, init_db
from core.services.qa_service import answer_question
from config.llm_config import load_llm_config
from core.services.job_manager import job_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Code Quality Intelligence Agent CLI."""
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=True))
@click.option(
    "--languages",
    default="py,js",
    help="Comma-separated list of languages to analyze (default: py,js)."
)
@click.option(
    "--out",
    default=None,
    type=click.Path(file_okay=False, dir_okay=True),
    help="Directory to store the generated report JSON (default: ./reports)."
)
@click.option(
    "--run-async",
    is_flag=True,
    default=False,
    help="Run analysis asynchronously."
)
@click.option(
    "--use-llm", "-l",
    is_flag=True,
    default=False,
    help="Enable LLM usage for enhanced analysis (default: False)."
)
@click.option(
    "--index-for-rag", "-r",
    is_flag=True,
    default=False,
    help="Build vector store index for RAG (default: False)."
)
def analyze(
    path: str,
    languages: str,
    out: str,
    run_async: bool,
    use_llm: bool,
    index_for_rag: bool
) -> int:
    """
    Analyze a code repository at PATH and generate a quality report.

    Additional options:
    --use-llm / -l : Enable LLM usage
    --index-for-rag / -r : Build vector store index after analysis
    """
    try:
        repo_path = Path(path).resolve()
        if not repo_path.exists():
            raise click.ClickException(f"Path does not exist: {repo_path}")

        # Parse languages
        languages_list: List[str] = [lang.strip() for lang in languages.split(",") if lang.strip()]
        if not languages_list:
            raise click.ClickException("No valid languages specified for analysis.")

        logger.info(f"Initializing database...")
        init_db()

        # Load LLM configuration
        config = load_llm_config()
        if use_llm:
            config.use_llm = True
            logger.info("LLM usage enabled via CLI flag.")

        if run_async:
            logger.info("Starting background analysis job...")
            job_id = job_manager.start_job(
                str(repo_path),
                languages_list,
                background=True,
                use_llm=use_llm,
                index_for_rag=index_for_rag
            )
            click.echo(json.dumps({"job_id": job_id, "status": "queued", "llm_enabled": use_llm}, indent=2))
            return 0

        # Synchronous analysis
        logger.info(f"Analyzing repository at {repo_path} for languages: {languages_list}")
        analysis = analyze_repo(
            str(repo_path),
            languages=languages_list,
            index_for_rag=index_for_rag
        )

        logger.info("Saving report to database...")
        report_id: int = save_report(analysis)

        # Decide output directory
        if out:
            out_dir = Path(out).resolve()
        else:
            out_dir = Path("./reports").resolve()

        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"report_{report_id}.json"

        with out_file.open("w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)

        summary = {
            "report_id": report_id,
            "summary": analysis.get("summary"),
            "overall_score": analysis.get("overall_score"),
            "llm_enabled": use_llm
        }
        click.echo(json.dumps(summary, indent=2))
        return 0

    except click.ClickException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
        raise click.ClickException(str(e))


@cli.command()
@click.argument("report_id", type=int)
@click.argument("question", type=str)
def qa(report_id: int, question: str) -> None:
    """
    Ask a natural language QUESTION about a report with REPORT_ID.
    """
    try:
        logger.info(f"Fetching report with ID {report_id}")
        report = get_report_by_id(report_id)
        if not report:
            raise click.ClickException(f"No report found with ID {report_id}")

        logger.info("Answering question...")
        answer = answer_question(report, question)
        click.echo(json.dumps({"answer": answer}, indent=2))

    except click.ClickException:
        raise
    except Exception as e:
        logger.error(f"Error in QA: {e}", exc_info=True)
        raise click.ClickException(str(e))


def main() -> None:
    """Entrypoint for CLI execution."""
    cli()


if __name__ == "__main__":
    main()
