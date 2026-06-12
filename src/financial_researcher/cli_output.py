"""Suppress noisy third-party warnings and logs for a clean CLI experience."""

from __future__ import annotations

import logging
import os
import warnings

try:
    from pydantic.warnings import ArbitraryTypeWarning, PydanticDeprecatedSince20
except ImportError:  # pragma: no cover - older pydantic
    ArbitraryTypeWarning = Warning  # type: ignore[misc, assignment]
    PydanticDeprecatedSince20 = DeprecationWarning  # type: ignore[misc, assignment]

_NOISY_LOGGERS = (
    "httpx",
    "httpcore",
    "openai",
    "LiteLLM",
    "litellm",
    "crewai",
    "urllib3",
    "chromadb",
    "mem0",
    "langsmith",
)

_SERPER_TOOL_LOGGER = "crewai_tools.tools.serper_dev_tool.serper_dev_tool"

_WARNINGS_CONFIGURED = False


def crew_quiet_enabled() -> bool:
    """Return True when BRIEFING_QUIET is set (hides CrewAI agent progress)."""
    flag = os.getenv("BRIEFING_QUIET", "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def crew_verbose_enabled() -> bool:
    """CrewAI agent/task progress is on by default; use --quiet to disable."""
    return not crew_quiet_enabled()


def configure_clean_cli_output() -> None:
    """Apply warning filters once; refresh logger levels when verbosity changes."""
    global _WARNINGS_CONFIGURED
    if not _WARNINGS_CONFIGURED:
        warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)
        warnings.filterwarnings("ignore", category=ArbitraryTypeWarning)
        warnings.filterwarnings("ignore", message=".*is not a Python type.*")
        warnings.filterwarnings("ignore", category=DeprecationWarning, module="mem0.*")
        _WARNINGS_CONFIGURED = True

    verbose = crew_verbose_enabled()
    level = logging.INFO if verbose else logging.WARNING
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(level)

    # SerperDevTool logs HTTP 400 as ERROR before raising; hide in --quiet mode.
    logging.getLogger(_SERPER_TOOL_LOGGER).setLevel(
        logging.INFO if verbose else logging.CRITICAL
    )
