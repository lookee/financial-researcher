"""Load application settings from defaults/settings.yaml and environment variables."""

from functools import lru_cache
import os
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

_SETTINGS_PATH = Path(__file__).parent / "defaults" / "settings.yaml"

if load_dotenv is not None:
    load_dotenv()


@lru_cache
def _load_yaml_settings() -> dict:
    if not _SETTINGS_PATH.exists():
        return {}
    with _SETTINGS_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def get_default_language() -> str:
    """Return the default briefing language.

    Priority: REPORT_LANGUAGE env var > settings.yaml > English.
    """
    env_language = os.getenv("REPORT_LANGUAGE", "").strip()
    if env_language:
        return env_language

    yaml_language = _load_yaml_settings().get("default_language", "English")
    if isinstance(yaml_language, str) and yaml_language.strip():
        return yaml_language.strip()

    return "English"


def get_model_profile_name() -> str:
    """Return the active model profile name.

    Priority: FR_MODEL_PROFILE env > settings.yaml model_profile >
    model_profiles.yaml default_profile > balanced.
    """
    env_profile = os.getenv("FR_MODEL_PROFILE", "").strip()
    if env_profile:
        return env_profile

    yaml_profile = _load_yaml_settings().get("model_profile", "")
    if isinstance(yaml_profile, str) and yaml_profile.strip():
        return yaml_profile.strip()

    from financial_researcher.agent_llm import get_default_profile_name

    return get_default_profile_name()


@lru_cache
def get_scrape_settings() -> dict[str, int | bool]:
    """Scrape tool options from settings.yaml (truncate_enabled defaults to True)."""
    scrape = _load_yaml_settings().get("scrape") or {}
    if not isinstance(scrape, dict):
        scrape = {}

    truncate_enabled = scrape.get("truncate_enabled", True)
    if isinstance(truncate_enabled, str):
        truncate_enabled = truncate_enabled.strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }

    max_chars = scrape.get("max_chars", 2500)
    try:
        max_chars = int(max_chars)
    except (TypeError, ValueError):
        max_chars = 2500

    return {
        "truncate_enabled": bool(truncate_enabled),
        "max_chars": max(500, min(max_chars, 20_000)),
    }


@lru_cache
def get_serper_settings() -> dict[str, bool]:
    """Serper API options (free_tier sanitisation defaults to True)."""
    env_flag = os.getenv("SERPER_FREE_TIER", "").strip().lower()
    if env_flag:
        free_tier = env_flag not in {"0", "false", "no", "off"}
        return {"free_tier": free_tier}

    serper = _load_yaml_settings().get("serper") or {}
    if not isinstance(serper, dict):
        serper = {}

    free_tier = serper.get("free_tier", True)
    if isinstance(free_tier, str):
        free_tier = free_tier.strip().lower() not in {"0", "false", "no", "off"}

    return {"free_tier": bool(free_tier)}


@lru_cache
def get_pipeline_settings() -> dict[str, int]:
    """Pipeline parallelism from settings.yaml (max_workers defaults to 4)."""
    pipeline = _load_yaml_settings().get("pipeline") or {}
    if not isinstance(pipeline, dict):
        pipeline = {}

    max_workers = pipeline.get("max_workers", 4)
    try:
        max_workers = int(max_workers)
    except (TypeError, ValueError):
        max_workers = 4

    return {"max_workers": max(1, min(max_workers, 16))}


@lru_cache
def get_benchmark_settings() -> list[dict[str, str]]:
    """Benchmark tickers for relative performance context (default: MIB + STOXX)."""
    raw = _load_yaml_settings().get("benchmarks") or []
    if not isinstance(raw, list):
        return [
            {"ticker": "FTSEMIB.MI", "name": "FTSE MIB"},
            {"ticker": "^STOXX", "name": "STOXX Europe 600"},
        ]
    benchmarks: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        ticker = str(entry.get("ticker", "")).strip()
        name = str(entry.get("name", ticker)).strip()
        if ticker:
            benchmarks.append({"ticker": ticker, "name": name})
    return benchmarks or [
        {"ticker": "FTSEMIB.MI", "name": "FTSE MIB"},
        {"ticker": "^STOXX", "name": "STOXX Europe 600"},
    ]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def _parse_email_list(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


@lru_cache
def get_email_settings() -> dict[str, str | bool | list[str]]:
    """Resend email delivery options from environment variables."""
    email = _load_yaml_settings().get("email") or {}
    if not isinstance(email, dict):
        email = {}

    env_to = os.getenv("BRIEFING_EMAIL_TO", "").strip()
    yaml_to = email.get("to", "")
    to_raw = env_to or (yaml_to if isinstance(yaml_to, str) else "")

    env_from = os.getenv("BRIEFING_EMAIL_FROM", "").strip()
    yaml_from = email.get("from", "")
    from_raw = env_from or (yaml_from if isinstance(yaml_from, str) else "")

    env_prefix = os.getenv("BRIEFING_EMAIL_SUBJECT_PREFIX", "").strip()
    yaml_prefix = email.get("subject_prefix", "[Watchlist]")
    subject_prefix = env_prefix or (
        yaml_prefix if isinstance(yaml_prefix, str) else "[Watchlist]"
    )

    auto_env = os.getenv("BRIEFING_EMAIL_AUTO", "").strip()
    auto_yaml = email.get("auto_send", False)
    if auto_env:
        auto_send = _env_bool("BRIEFING_EMAIL_AUTO", False)
    elif isinstance(auto_yaml, bool):
        auto_send = auto_yaml
    elif isinstance(auto_yaml, str):
        auto_send = auto_yaml.strip().lower() not in {"0", "false", "no", "off"}
    else:
        auto_send = False

    return {
        "api_key": os.getenv("RESEND_API_KEY", "").strip(),
        "from_address": from_raw.strip(),
        "to_addresses": _parse_email_list(to_raw),
        "subject_prefix": str(subject_prefix).strip() or "[Watchlist]",
        "auto_send": auto_send,
    }


def email_delivery_configured() -> bool:
    """True when Resend can send (API key, sender and at least one recipient)."""
    cfg = get_email_settings()
    return bool(cfg["api_key"] and cfg["from_address"] and cfg["to_addresses"])


def clamp_openrouter_auto_tradeoff(value: int) -> int:
    """Clamp OpenRouter Auto savings level to 1–10 (maps to cost_quality_tradeoff)."""
    return max(1, min(10, int(value)))


def parse_openrouter_auto_tradeoff(raw: str | int | float | None) -> int | None:
    """Parse a savings level 1–10, or None when unset/invalid."""
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None
    try:
        return clamp_openrouter_auto_tradeoff(int(raw))
    except (TypeError, ValueError):
        return None


@lru_cache
def get_openrouter_auto_tradeoff_from_config() -> int | None:
    """OpenRouter Auto savings level from env or settings.yaml only (not profile)."""
    env_value = parse_openrouter_auto_tradeoff(
        os.getenv("OPENROUTER_AUTO_TRADEOFF", "").strip() or None
    )
    if env_value is not None:
        return env_value

    openrouter = _load_yaml_settings().get("openrouter") or {}
    if isinstance(openrouter, dict):
        return parse_openrouter_auto_tradeoff(openrouter.get("auto_tradeoff"))
    return None


@lru_cache
def get_report_settings() -> dict[str, bool]:
    """Briefing report options (run-metadata footer enabled by default)."""
    report = _load_yaml_settings().get("report") or {}
    if not isinstance(report, dict):
        report = {}

    env_flag = os.getenv("BRIEFING_RUN_METADATA", "").strip()
    if env_flag:
        include_run_metadata = _env_bool("BRIEFING_RUN_METADATA", True)
    else:
        include = report.get("include_run_metadata", True)
        if isinstance(include, str):
            include_run_metadata = include.strip().lower() not in {
                "0",
                "false",
                "no",
                "off",
            }
        else:
            include_run_metadata = bool(include)

    return {"include_run_metadata": include_run_metadata}
