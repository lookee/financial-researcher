#!/usr/bin/env python
"""CLI for Milan watchlist executive briefings.

Forked and extended from CrewAI patterns in Ed Donner's Udemy course:
https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/
"""

import argparse
import os
from pathlib import Path

from financial_researcher.crew import WatchlistBriefingCrew
from financial_researcher.services.briefing_postprocess import postprocess_briefing
from financial_researcher.services.watchlist_context import (
    briefing_output_path,
    infer_milan_session,
)
from financial_researcher.services.watchlist_pipeline import (
    VALID_SESSIONS,
    WatchlistPipeline,
)
from financial_researcher.settings import get_default_language

WATCHLIST_PATH = Path("src/financial_researcher/config/watchlist.yaml")


def _ensure_dirs() -> None:
    os.makedirs("output/briefings", exist_ok=True)
    os.makedirs("data/identity", exist_ok=True)
    os.makedirs("data/market", exist_ok=True)


def run_briefing(
    *,
    session: str | None = None,
    language: str | None = None,
    force: bool = False,
    watchlist_path: Path | None = None,
) -> str:
    """Generate a unified executive briefing for the configured watchlist."""
    _ensure_dirs()
    chosen_session = session or infer_milan_session()
    if chosen_session not in VALID_SESSIONS:
        raise ValueError(
            f"Invalid session {chosen_session!r}. "
            f"Choose from: {', '.join(VALID_SESSIONS)}"
        )

    print(f"Session: {chosen_session} (Milan)")
    print("Loading watchlist market data...")
    pipeline = WatchlistPipeline()
    inputs = pipeline.collect(
        watchlist_path,
        force=force,
        language=language,
        session=chosen_session,
    )

    output_file = briefing_output_path(chosen_session)
    briefing_crew = WatchlistBriefingCrew()
    briefing_crew.executive_briefing_task().output_file = output_file
    result = briefing_crew.crew().kickoff(inputs=inputs)

    output_path = Path(output_file)
    raw_markdown = output_path.read_text(encoding="utf-8") if output_path.exists() else (result.raw or "")
    processed, warnings = postprocess_briefing(raw_markdown, inputs)
    output_path.write_text(processed, encoding="utf-8")

    for warning in warnings:
        print(f"Post-process warning: {warning}")

    print(f"\n\n=== WATCHLIST BRIEFING ({chosen_session}) ===\n\n")
    print(processed)
    print(f"\n\nBriefing saved to {output_file}")
    return output_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Financial Researcher — Milan watchlist executive briefing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run briefing
  uv run briefing --session close
  uv run briefing --force --language Italian
        """,
    )
    parser.add_argument(
        "--session",
        choices=list(VALID_SESSIONS),
        default=None,
        help="Milan session (default: infer from current Europe/Rome time)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help=f"Briefing language (default: {get_default_language()} from settings)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh cached identity and market data",
    )
    parser.add_argument(
        "--watchlist",
        type=Path,
        default=WATCHLIST_PATH,
        help="Path to watchlist YAML",
    )
    return parser


def cli(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    run_briefing(
        session=args.session,
        language=args.language,
        force=args.force,
        watchlist_path=args.watchlist,
    )


def briefing_cli() -> None:
    """Entry point: uv run briefing"""
    cli()


if __name__ == "__main__":
    cli()
