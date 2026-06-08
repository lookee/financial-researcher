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
