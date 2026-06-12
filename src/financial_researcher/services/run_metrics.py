"""Persist and display token usage metrics for briefing runs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from financial_researcher.paths import metrics_dir

MILAN_TZ = ZoneInfo("Europe/Rome")


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


def build_run_metrics_payload(
    *,
    session: str,
    language: str,
    instrument_count: int,
    usage: dict[str, int],
    duration_seconds: float,
    warnings: list[str],
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Assemble the JSON document written after each briefing run."""
    moment = timestamp or datetime.now(MILAN_TZ)
    return {
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
