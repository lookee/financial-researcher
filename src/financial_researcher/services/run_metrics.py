"""Persist and display token usage metrics for briefing runs."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from financial_researcher.paths import metrics_dir

MILAN_TZ = ZoneInfo("Europe/Rome")

_RUN_METADATA_START = "<!-- financial-researcher:run-metadata -->"
_RUN_METADATA_END = "<!-- /financial-researcher:run-metadata -->"

_AGENT_LABELS: dict[str, dict[str, str]] = {
    "English": {
        "market": "Market analyst",
        "news": "News analyst",
        "outlook": "Outlook analyst",
        "calendar": "Calendar analyst",
        "chief": "Chief strategist",
    },
    "Italian": {
        "market": "Analista mercato",
        "news": "Analista news",
        "outlook": "Analista outlook",
        "calendar": "Analista calendario",
        "chief": "Chief strategist",
    },
}

_METADATA_COPY: dict[str, dict[str, str]] = {
    "English": {
        "heading": "Run metadata",
        "profile": "Model profile",
        "duration": "Processing time",
        "requests": "LLM requests",
        "tokens": "Tokens (prompt / completion / total)",
        "agents_heading": "Models by agent",
        "agent_col": "Agent",
        "model_col": "Model",
        "openrouter_savings": "OpenRouter savings (1–10)",
    },
    "Italian": {
        "heading": "Informazioni di elaborazione",
        "profile": "Profilo modelli",
        "duration": "Tempo di elaborazione",
        "requests": "Richieste LLM",
        "tokens": "Token (prompt / completion / totale)",
        "agents_heading": "Modelli per agente",
        "agent_col": "Agente",
        "model_col": "Modello",
        "openrouter_savings": "Risparmio OpenRouter (1–10)",
    },
}


def extract_usage_metrics(crew: Any) -> dict[str, int]:
    """Read CrewAI usage metrics defensively across library versions."""
    metrics = getattr(crew, "usage_metrics", None)
    if metrics is None and hasattr(crew, "calculate_usage_metrics"):
        try:
            metrics = crew.calculate_usage_metrics()
        except Exception:
            metrics = None

    if metrics is None:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "successful_requests": 0,
        }

    if hasattr(metrics, "model_dump"):
        payload = metrics.model_dump()
    elif isinstance(metrics, dict):
        payload = metrics
    else:
        payload = {
            "prompt_tokens": getattr(metrics, "prompt_tokens", 0),
            "completion_tokens": getattr(metrics, "completion_tokens", 0),
            "total_tokens": getattr(metrics, "total_tokens", 0),
            "successful_requests": getattr(metrics, "successful_requests", 0),
        }

    return {
        "prompt_tokens": int(payload.get("prompt_tokens") or 0),
        "completion_tokens": int(payload.get("completion_tokens") or 0),
        "total_tokens": int(payload.get("total_tokens") or 0),
        "successful_requests": int(payload.get("successful_requests") or 0),
    }


def metrics_output_path(*, date_str: str, session: str) -> Path:
    """Path for a run metrics JSON file."""
    return metrics_dir() / f"run_{date_str}_{session}.json"


def build_agent_models_map() -> dict[str, str]:
    """Return resolved model id per agent for the active profile."""
    from financial_researcher.agent_llm import _AGENT_KEYS, resolve_agent_model

    return {agent: resolve_agent_model(agent) for agent in _AGENT_KEYS}


def format_duration(seconds: float) -> str:
    """Human-readable duration for reports."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining = seconds % 60
    if minutes < 60:
        return f"{minutes}m {remaining:.0f}s"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m {remaining:.0f}s"


def _format_token_count(value: int) -> str:
    return f"{value:,}"


def _metadata_copy(language: str) -> dict[str, str]:
    key = "Italian" if language.strip().lower().startswith("ital") else "English"
    return _METADATA_COPY[key]


def _agent_labels(language: str) -> dict[str, str]:
    key = "Italian" if language.strip().lower().startswith("ital") else "English"
    return _AGENT_LABELS[key]


def strip_run_metadata_footer(markdown: str) -> str:
    """Remove a previously appended run-metadata block, if present."""
    pattern = re.compile(
        rf"\n?{re.escape(_RUN_METADATA_START)}.*?{re.escape(_RUN_METADATA_END)}\n?",
        re.DOTALL,
    )
    return pattern.sub("", markdown).rstrip()


def format_run_metadata_footer(
    *,
    metrics_payload: dict[str, Any],
    language: str,
) -> str:
    """Build the markdown footer block for run metadata."""
    copy = _metadata_copy(language)
    labels = _agent_labels(language)
    agent_models: dict[str, str] = metrics_payload.get("agent_models") or {}

    summary_rows = [
        f"| {copy['profile']} | {metrics_payload.get('model_profile', '—')} |",
        f"| {copy['duration']} | {format_duration(float(metrics_payload.get('duration_seconds', 0)))} |",
        f"| {copy['requests']} | {int(metrics_payload.get('successful_requests', 0))} |",
        (
            f"| {copy['tokens']} | "
            f"{_format_token_count(int(metrics_payload.get('prompt_tokens', 0)))} / "
            f"{_format_token_count(int(metrics_payload.get('completion_tokens', 0)))} / "
            f"{_format_token_count(int(metrics_payload.get('total_tokens', 0)))} |"
        ),
    ]
    tradeoff = metrics_payload.get("openrouter_auto_tradeoff")
    if tradeoff is not None:
        summary_rows.append(f"| {copy['openrouter_savings']} | {int(tradeoff)} |")

    agent_rows = [
        f"| {labels[agent]} | `{model}` |"
        for agent, model in agent_models.items()
        if agent in labels
    ]

    lines = [
        _RUN_METADATA_START,
        f"## {copy['heading']}",
        "",
        "| | |",
        "|---|---|",
        *summary_rows,
        "",
        f"**{copy['agents_heading']}**",
        "",
        f"| {copy['agent_col']} | {copy['model_col']} |",
        "|---|---|",
        *agent_rows,
        _RUN_METADATA_END,
    ]
    return "\n".join(lines)


def append_run_metadata_footer(
    markdown: str,
    *,
    metrics_payload: dict[str, Any],
    language: str,
) -> str:
    """Append (or replace) the run-metadata footer at the end of the briefing."""
    base = strip_run_metadata_footer(markdown)
    footer = format_run_metadata_footer(
        metrics_payload=metrics_payload,
        language=language,
    )
    return f"{base}\n\n{footer}\n"


def build_run_metrics_payload(
    *,
    session: str,
    language: str,
    instrument_count: int,
    usage: dict[str, int],
    duration_seconds: float,
    warnings: list[str],
    model_profile: str | None = None,
    agent_models: dict[str, str] | None = None,
    openrouter_auto_tradeoff: int | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Assemble the JSON document written after each briefing run."""
    moment = timestamp or datetime.now(MILAN_TZ)
    payload: dict[str, Any] = {
        "timestamp": moment.isoformat(),
        "session": session,
        "language": language,
        "instrument_count": instrument_count,
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "total_tokens": usage["total_tokens"],
        "successful_requests": usage["successful_requests"],
        "duration_seconds": round(duration_seconds, 2),
        "postprocess_warnings": warnings,
    }
    if model_profile:
        payload["model_profile"] = model_profile
    if agent_models:
        payload["agent_models"] = agent_models
    if openrouter_auto_tradeoff is not None:
        payload["openrouter_auto_tradeoff"] = int(openrouter_auto_tradeoff)
    return payload


def write_run_metrics(
    path: Path,
    payload: dict[str, Any],
) -> Path:
    """Write metrics JSON and return the path written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def format_metrics_summary(
    usage: dict[str, int],
    *,
    warnings: list[str],
) -> str:
    """One-line summary for CLI output."""
    warning_count = len(warnings)
    return (
        f"Tokens: prompt={usage['prompt_tokens']} completion={usage['completion_tokens']} "
        f"| requests={usage['successful_requests']} | warnings={warning_count}"
    )
