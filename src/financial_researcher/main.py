#!/usr/bin/env python
"""CLI entry points for ISIN-based financial research reports.

Forked and extended from CrewAI patterns in Ed Donner's Udemy course:
https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import yaml

from financial_researcher.crew import InstrumentCrew
from financial_researcher.services.isin_resolver import IsinResolver
from financial_researcher.services.market_data import MarketDataService
from financial_researcher.services.report_builder import build_crew_inputs, output_path_for
from financial_researcher.settings import get_default_language

WATCHLIST_PATH = Path("src/financial_researcher/config/watchlist.yaml")
REPORTS_DIR = Path("output/reports")
IDENTITY_DIR = Path("data/identity")
ISIN_LENGTH = 12


def _ensure_dirs() -> None:
    """Create output and data directories if missing."""
    os.makedirs("output", exist_ok=True)
    os.makedirs("output/reports", exist_ok=True)
    os.makedirs("data/identity", exist_ok=True)
    os.makedirs("data/market", exist_ok=True)


def _load_watchlist(path: Path | None = None) -> dict:
    watchlist_path = path or WATCHLIST_PATH
    with watchlist_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_isin(
    isin: str,
    force: bool = False,
    ticker: str | None = None,
    instrument_type: str | None = None,
) -> None:
    """Resolve an ISIN to a cached InstrumentIdentity."""
    _ensure_dirs()
    resolver = IsinResolver()
    identity = resolver.resolve(
        isin=isin,
        force_refresh=force,
        preferred_ticker=ticker,
        manual_ticker=ticker,
        manual_type=instrument_type,
    )
    print(f"Resolved ISIN: {identity.isin}")
    print(f"  Name:     {identity.name}")
    print(f"  Type:     {identity.instrument_type}")
    print(f"  Ticker:   {identity.primary_ticker}")
    print(f"  Exchange: {identity.exchange}")
    print(f"  Source:   {identity.source}")
    print(f"  Cache:    data/identity/{identity.isin}.json")


def report(
    isin: str,
    ticker: str | None = None,
    language: str | None = None,
    force: bool = False,
    instrument_type: str | None = None,
) -> str:
    """Run the full pipeline: resolve → market data → CrewAI → Markdown report."""
    report_language = language or get_default_language()
    _ensure_dirs()
    resolver = IsinResolver()
    identity = resolver.resolve(
        isin=isin,
        force_refresh=force,
        preferred_ticker=ticker,
        manual_ticker=ticker,
        manual_type=instrument_type,
    )

    market = MarketDataService()
    snapshot = market.get_snapshot(identity)
    inputs = build_crew_inputs(identity, snapshot, language=report_language)
    output_file = output_path_for(identity)

    instrument_crew = InstrumentCrew()
    instrument_crew.compose_report_task().output_file = output_file
    result = instrument_crew.crew().kickoff(inputs=inputs)

    print(f"\n\n=== REPORT {identity.isin} ===\n\n")
    print(result.raw)
    print(f"\n\nReport saved to {output_file}")
    return output_file


def run_watchlist(watchlist_path: Path | None = None) -> list[str]:
    """Generate reports for every instrument listed in watchlist.yaml."""
    _ensure_dirs()
    config = _load_watchlist(watchlist_path)
    language = config.get("language") or get_default_language()
    outputs: list[str] = []

    for item in config.get("instruments", []):
        isin = item["isin"]
        print(f"\n--- Processing {isin} ({item.get('name', '')}) ---")
        output = report(
            isin=isin,
            ticker=item.get("ticker"),
            language=language,
            instrument_type=item.get("type"),
        )
        outputs.append(output)

    summary_path = Path(f"output/watchlist_{date.today().isoformat()}.md")
    with summary_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# Watchlist report — {date.today().isoformat()}\n\n")
        for output in outputs:
            handle.write(f"- [{Path(output).name}]({output})\n")

    print(f"\nWatchlist index: {summary_path}")
    return outputs


def _isin_from_report_path(path: Path) -> str | None:
    """Extract a 12-character ISIN prefix from a report filename."""
    stem = path.stem
    if len(stem) < ISIN_LENGTH + 1:
        return None
    isin = stem[:ISIN_LENGTH].upper()
    if not isin[:2].isalpha() or not isin[2:].isalnum():
        return None
    return isin


def refresh_reports(
    language: str | None = None,
    reports_dir: Path | None = None,
) -> list[str]:
    """Regenerate reports for each unique ISIN found under output/reports/."""
    report_language = language or get_default_language()
    _ensure_dirs()
    directory = reports_dir or REPORTS_DIR
    if not directory.exists():
        print(f"No reports directory: {directory}")
        return []

    seen_isins: set[str] = set()
    outputs: list[str] = []

    for report_path in sorted(directory.glob("*.md")):
        isin = _isin_from_report_path(report_path)
        if not isin or isin in seen_isins:
            continue
        seen_isins.add(isin)

        identity_path = IDENTITY_DIR / f"{isin}.json"
        if not identity_path.exists():
            print(f"Skip {isin}: identity not in cache ({identity_path})")
            continue

        with identity_path.open(encoding="utf-8") as handle:
            identity_data = json.load(handle)
        ticker = identity_data.get("primary_ticker")
        instrument_type = identity_data.get("instrument_type")

        print(f"\n--- Refreshing {isin} ({ticker}) from {report_path.name} ---")
        output = report(
            isin=isin,
            ticker=ticker,
            language=report_language,
            force=True,
            instrument_type=instrument_type,
        )
        outputs.append(output)

    if not outputs:
        print("No reports updated.")
    else:
        print(f"\nUpdated {len(outputs)} report(s).")
    return outputs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Financial Researcher — ISIN-based stock and ETF reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run report US67066G1040 NVDA
  uv run report IE00BK5BQT80 VWCE.DE
  uv run report US67066G1040
  uv run watchlist
  uv run refresh-reports
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    report_parser = subparsers.add_parser("report", help="Generate a report from ISIN")
    report_parser.add_argument("isin", help="ISIN code")
    report_parser.add_argument("ticker", nargs="?", help="Exchange ticker (e.g. NVDA)")
    report_parser.add_argument(
        "--language",
        default=None,
        help=f"Report language (default: {get_default_language()} from settings)",
    )
    report_parser.add_argument("--force", action="store_true")
    report_parser.add_argument("--type", choices=["stock", "etf"])

    resolve_parser = subparsers.add_parser("resolve", help="Resolve and cache ISIN identity")
    resolve_parser.add_argument("isin")
    resolve_parser.add_argument("ticker", nargs="?")
    resolve_parser.add_argument("--force", action="store_true")
    resolve_parser.add_argument("--type", choices=["stock", "etf"])

    subparsers.add_parser("watchlist", help="Generate reports for watchlist.yaml")

    refresh_parser = subparsers.add_parser(
        "refresh-reports",
        help="Regenerate reports already present in output/reports/",
    )
    refresh_parser.add_argument(
        "--language",
        default=None,
        help=f"Report language (default: {get_default_language()} from settings)",
    )

    return parser


def cli(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "report":
        report(args.isin, args.ticker, args.language, args.force, args.type)
    elif args.command == "resolve":
        resolve_isin(args.isin, args.force, args.ticker, args.type)
    elif args.command == "watchlist":
        run_watchlist()
    elif args.command == "refresh-reports":
        refresh_reports(language=args.language)
    else:
        parser.print_help()
        sys.exit(1)


def report_cli() -> None:
    """Entry point: uv run report ISIN [TICKER]"""
    parser = argparse.ArgumentParser(description="Generate a financial report from ISIN")
    parser.add_argument("isin", help="ISIN code")
    parser.add_argument("ticker", nargs="?", help="Exchange ticker (e.g. NVDA)")
    parser.add_argument(
        "--language",
        default=None,
        help=f"Report language (default: {get_default_language()} from settings)",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--type", choices=["stock", "etf"])
    args = parser.parse_args()
    report(args.isin, args.ticker, args.language, args.force, args.type)


def resolve_cli() -> None:
    """Entry point: uv run resolve ISIN [TICKER]"""
    parser = argparse.ArgumentParser(description="Resolve and cache ISIN identity")
    parser.add_argument("isin", help="ISIN code")
    parser.add_argument("ticker", nargs="?", help="Exchange ticker (e.g. NVDA)")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--type", choices=["stock", "etf"])
    args = parser.parse_args()
    resolve_isin(args.isin, args.force, args.ticker, args.type)


def watchlist_cli() -> None:
    run_watchlist()


def refresh_reports_cli() -> None:
    """Entry point: uv run refresh-reports"""
    parser = argparse.ArgumentParser(
        description="Regenerate reports already present in output/reports/",
    )
    parser.add_argument(
        "--language",
        default=None,
        help=f"Report language (default: {get_default_language()} from settings)",
    )
    args = parser.parse_args()
    refresh_reports(language=args.language)


if __name__ == "__main__":
    cli()
