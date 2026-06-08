"""User configuration paths (outside package source)."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
WATCHLIST_TEMPLATE = PACKAGE_DIR / "config" / "watchlist.example.yaml"


def user_config_dir() -> Path:
    """Global per-user config directory (~/.config/financial_researcher)."""
    override = os.getenv("FINANCIAL_RESEARCHER_CONFIG_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "financial_researcher"


def project_config_dir() -> Path:
    """Project-local user config (./config in the current working directory)."""
    return Path.cwd() / "config"


def default_watchlist_path() -> Path:
    """Preferred watchlist location when none is passed explicitly."""
    return project_config_dir() / "watchlist.yaml"


def resolve_watchlist_path(explicit: Path | None = None) -> Path:
    """Resolve watchlist YAML path from CLI, env, or user config locations."""
    if explicit is not None:
        return explicit.expanduser().resolve()

    env_path = os.getenv("WATCHLIST_PATH", "").strip()
    if env_path:
        return Path(env_path).expanduser().resolve()

    project_path = project_config_dir() / "watchlist.yaml"
    if project_path.is_file():
        return project_path.resolve()

    user_path = user_config_dir() / "watchlist.yaml"
    if user_path.is_file():
        return user_path.resolve()

    return default_watchlist_path().resolve()


def ensure_watchlist_exists(explicit: Path | None = None) -> Path:
    """Return watchlist path, creating ./config/watchlist.yaml from template if missing."""
    watchlist_path = resolve_watchlist_path(explicit)
    if watchlist_path.is_file():
        return watchlist_path

    watchlist_path.parent.mkdir(parents=True, exist_ok=True)
    if WATCHLIST_TEMPLATE.is_file():
        watchlist_path.write_text(
            WATCHLIST_TEMPLATE.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    else:
        watchlist_path.write_text("instruments: []\n", encoding="utf-8")

    print(
        f"Created {watchlist_path} from template — edit your instruments there."
    )
    return watchlist_path
