"""User configuration paths (outside package source)."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def watchlist_template_path() -> Path:
    """Watchlist template: ./config/watchlist.yaml.example in a dev checkout, else packaged copy."""
    local_example = Path.cwd() / "config" / "watchlist.yaml.example"
    if local_example.is_file():
        return local_example
    packaged = PACKAGE_DIR / "defaults" / "watchlist.yaml.example"
    return packaged


def project_home() -> Path:
    """Base directory for runtime output and data (default: current working directory)."""
    override = os.getenv("FINANCIAL_RESEARCHER_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path.cwd()


def output_dir() -> Path:
    return project_home() / "output"


def briefings_dir() -> Path:
    return output_dir() / "briefings"


def metrics_dir() -> Path:
    return output_dir() / "metrics"


def data_dir() -> Path:
    return project_home() / "data"


def identity_data_dir() -> Path:
    return data_dir() / "identity"


def market_data_dir() -> Path:
    return data_dir() / "market"


def ensure_runtime_dirs() -> None:
    """Create output, data, and project config directories if missing."""
    briefings_dir().mkdir(parents=True, exist_ok=True)
    metrics_dir().mkdir(parents=True, exist_ok=True)
    identity_data_dir().mkdir(parents=True, exist_ok=True)
    market_data_dir().mkdir(parents=True, exist_ok=True)
    project_config_dir().mkdir(parents=True, exist_ok=True)


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
    template = watchlist_template_path()
    if template.is_file():
        watchlist_path.write_text(
            template.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    else:
        watchlist_path.write_text("instruments: []\n", encoding="utf-8")

    print(
        f"Created {watchlist_path} from template — edit your instruments there."
    )
    return watchlist_path
