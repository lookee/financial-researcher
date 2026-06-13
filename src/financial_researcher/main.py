#!/usr/bin/env python
"""CLI for Milan watchlist executive briefings.

Forked and extended from CrewAI patterns in Ed Donner's Udemy course:
https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/
"""

from financial_researcher.cli_output import configure_clean_cli_output

configure_clean_cli_output()

import argparse
import os
import time
from pathlib import Path

from financial_researcher.agent_llm import (
    clear_profile_caches,
    describe_active_profile,
    list_model_profile_names,
    resolve_active_profile_name,
    resolve_openrouter_auto_tradeoff,
    uses_openrouter_auto_routing,
)
from financial_researcher.crew import WatchlistBriefingCrew
from financial_researcher.paths import default_watchlist_path, ensure_runtime_dirs
from financial_researcher.services.briefing_postprocess import postprocess_briefing
from financial_researcher.services.briefing_validator import (
    format_validation_summary,
    validate_briefing,
)
from financial_researcher.services.briefing_email import BriefingEmailError, send_briefing_email
from financial_researcher.services.run_metrics import (
    append_run_metadata_footer,
    build_agent_models_map,
    build_run_metrics_payload,
    extract_usage_metrics,
    format_metrics_summary,
    metrics_output_path,
    write_run_metrics,
)
from financial_researcher.services.watchlist_context import (
    briefing_output_path,
    infer_milan_session,
)
from financial_researcher.services.watchlist_pipeline import (
    VALID_SESSIONS,
    WatchlistPipeline,
)
from financial_researcher.settings import (
    email_delivery_configured,
    get_default_language,
    get_email_settings,
    get_model_profile_name,
    get_report_settings,
)

WATCHLIST_PATH = default_watchlist_path()


def run_briefing(
    *,
    session: str | None = None,
    language: str | None = None,
    force: bool = False,
    watchlist_path: Path | None = None,
    model_profile: str | None = None,
    send_email: bool | None = None,
    include_run_metadata: bool | None = None,
    openrouter_tradeoff: int | None = None,
) -> str:
    """Generate a unified executive briefing for the configured watchlist."""
    ensure_runtime_dirs()
    chosen_session = session or infer_milan_session()
    if chosen_session not in VALID_SESSIONS:
        raise ValueError(
            f"Invalid session {chosen_session!r}. "
            f"Choose from: {', '.join(VALID_SESSIONS)}"
        )

    if model_profile:
        os.environ["FR_MODEL_PROFILE"] = model_profile

    if openrouter_tradeoff is not None:
        os.environ["OPENROUTER_AUTO_TRADEOFF"] = str(openrouter_tradeoff)

    if model_profile or openrouter_tradeoff is not None:
        clear_profile_caches()

    if openrouter_tradeoff is not None and not uses_openrouter_auto_routing():
        print(
            "\n▸ Warning: --openrouter-tradeoff applies only to openrouter_auto_* "
            "profiles; the active profile does not use OpenRouter Auto routing."
        )

    print(f"\n▸ Session: {chosen_session} (Milan)")
    print(f"▸ Model profile: {describe_active_profile()}")
    print("▸ Loading watchlist market data...")
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
    crew = briefing_crew.crew()
    started_at = time.perf_counter()
    result = crew.kickoff(inputs=inputs)
    duration_seconds = time.perf_counter() - started_at

    output_path = Path(output_file)
    raw_markdown = output_path.read_text(encoding="utf-8") if output_path.exists() else (result.raw or "")
    processed, warnings = postprocess_briefing(raw_markdown, inputs)
    validation_warnings = validate_briefing(processed, inputs)

    usage = extract_usage_metrics(crew)
    metrics_path = metrics_output_path(
        date_str=inputs.get("current_date", ""),
        session=chosen_session,
    )
    metrics_payload = build_run_metrics_payload(
        session=chosen_session,
        language=inputs.get("language", get_default_language()),
        instrument_count=int(inputs.get("instrument_count", 0)),
        usage=usage,
        duration_seconds=duration_seconds,
        warnings=warnings + validation_warnings,
        model_profile=resolve_active_profile_name(),
        agent_models=build_agent_models_map(),
        openrouter_auto_tradeoff=(
            resolve_openrouter_auto_tradeoff()
            if uses_openrouter_auto_routing()
            else None
        ),
    )
    write_run_metrics(metrics_path, metrics_payload)

    show_metadata = (
        include_run_metadata
        if include_run_metadata is not None
        else get_report_settings()["include_run_metadata"]
    )
    if show_metadata:
        processed = append_run_metadata_footer(
            processed,
            metrics_payload=metrics_payload,
            language=inputs.get("language", get_default_language()),
        )

    output_path.write_text(processed, encoding="utf-8")

    all_warnings = warnings + validation_warnings
    if warnings:
        print("\n▸ Post-process warnings:")
        for warning in warnings:
            print(f"  • {warning}")

    print(f"\n▸ {format_validation_summary(validation_warnings)}")
    if validation_warnings:
        for warning in validation_warnings:
            print(f"  • {warning}")

    print(f"\n▸ {format_metrics_summary(usage, warnings=all_warnings)}")
    print(f"▸ Briefing saved to {output_file}")
    print(f"▸ Metrics saved to {metrics_path}")

    should_email = send_email if send_email is not None else get_email_settings()["auto_send"]
    if should_email:
        try:
            email_id = send_briefing_email(
                markdown_text=processed,
                markdown_path=output_path,
                session=chosen_session,
                date_str=inputs.get("current_date", ""),
                language=inputs.get("language", get_default_language()),
            )
            recipients = ", ".join(get_email_settings()["to_addresses"])
            print(f"▸ Email sent via Resend to {recipients} (id: {email_id})")
        except BriefingEmailError as exc:
            print(f"\n▸ Email delivery failed: {exc}")

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
  uv run briefing --model-profile openrouter_auto_balanced --openrouter-tradeoff 3
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
        help=f"Watchlist YAML path (default: {default_watchlist_path()})",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Hide CrewAI agent progress (default: show task/agent status). Same as BRIEFING_QUIET=1",
    )
    profile_choices = list_model_profile_names()
    parser.add_argument(
        "--model-profile",
        choices=profile_choices if profile_choices else None,
        default=None,
        help=(
            f"Model lineup profile (default: {get_model_profile_name()}). "
            f"Choices: {', '.join(profile_choices)}. "
            "Same as FR_MODEL_PROFILE."
        ),
    )
    email_help = "Send the briefing as HTML email via Resend after saving."
    if email_delivery_configured():
        email_help += " Configured in .env (RESEND_API_KEY, BRIEFING_EMAIL_FROM, BRIEFING_EMAIL_TO)."
    else:
        email_help += " Requires RESEND_API_KEY, BRIEFING_EMAIL_FROM and BRIEFING_EMAIL_TO in .env."
    parser.add_argument(
        "--email",
        action="store_true",
        help=email_help,
    )
    parser.add_argument(
        "--no-run-metadata",
        action="store_true",
        help="Omit the run-metadata footer (processing time, models, tokens) from the briefing",
    )
    parser.add_argument(
        "--openrouter-tradeoff",
        type=int,
        choices=range(1, 11),
        metavar="1-10",
        default=None,
        help=(
            "OpenRouter Auto savings override (1 = quality, 10 = max savings). "
            "Beats the profile preset (quality=1, balanced=7, economy=10). "
            "Same as OPENROUTER_AUTO_TRADEOFF. Only for openrouter_auto_* profiles."
        ),
    )
    return parser


def cli(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.quiet:
        os.environ["BRIEFING_QUIET"] = "1"
        configure_clean_cli_output()
    run_briefing(
        session=args.session,
        language=args.language,
        force=args.force,
        watchlist_path=args.watchlist,
        model_profile=args.model_profile,
        send_email=args.email or None,
        include_run_metadata=False if args.no_run_metadata else None,
        openrouter_tradeoff=args.openrouter_tradeoff,
    )


def briefing_cli() -> None:
    """Entry point: uv run briefing"""
    cli()


if __name__ == "__main__":
    cli()
