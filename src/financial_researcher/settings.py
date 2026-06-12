"""Load application settings from config/settings.yaml and environment variables."""

from functools import lru_cache
import os
from pathlib import Path

import yaml

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

_SETTINGS_PATH = Path(__file__).parent / "config" / "settings.yaml"

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
