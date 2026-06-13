"""Per-agent LLM model and reasoning-effort configuration.

Lineups are defined in defaults/model_profiles.yaml (balanced, frontier, budget, anthropic, deepseek, multi, free_groq, free_openrouter_nex).
Select a profile via FR_MODEL_PROFILE, defaults/settings.yaml model_profile, or --model-profile.
Per-agent FR_MODEL_* env vars still override the active profile for that agent.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from crewai import LLM

_AGENT_KEYS: tuple[str, ...] = ("market", "news", "outlook", "calendar", "chief")

_AGENT_MODEL_ENV: dict[str, str] = {
    "market": "FR_MODEL_MARKET",
    "news": "FR_MODEL_NEWS",
    "outlook": "FR_MODEL_OUTLOOK",
    "calendar": "FR_MODEL_CALENDAR",
    "chief": "FR_MODEL_CHIEF",
}

_PROFILES_PATH = Path(__file__).parent / "defaults" / "model_profiles.yaml"
_FALLBACK_DEFAULT_PROFILE = "balanced"


@lru_cache
def _load_profiles_document() -> dict[str, Any]:
    if not _PROFILES_PATH.exists():
        return {"default_profile": _FALLBACK_DEFAULT_PROFILE, "profiles": {}}
    with _PROFILES_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data


def clear_profile_caches() -> None:
    """Clear cached profile YAML (for tests)."""
    _load_profiles_document.cache_clear()


def list_model_profile_names() -> list[str]:
    profiles = _load_profiles_document().get("profiles") or {}
    return sorted(profiles.keys())


def get_default_profile_name() -> str:
    default = _load_profiles_document().get("default_profile", _FALLBACK_DEFAULT_PROFILE)
    if isinstance(default, str) and default.strip():
        return default.strip()
    return _FALLBACK_DEFAULT_PROFILE


def resolve_active_profile_name() -> str:
    """Profile name from env, settings.yaml, or model_profiles default."""
    from financial_researcher.settings import get_model_profile_name

    return get_model_profile_name()


def get_profile_description(profile_name: str | None = None) -> str:
    name = profile_name or resolve_active_profile_name()
    profiles = _load_profiles_document().get("profiles") or {}
    profile = profiles.get(name) or {}
    description = profile.get("description", "")
    if isinstance(description, str):
        return " ".join(description.split())
    return ""


def _agent_config_for_profile(profile_name: str, agent: str) -> dict[str, str]:
    profiles = _load_profiles_document().get("profiles") or {}
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        available = ", ".join(list_model_profile_names()) or "(none)"
        raise ValueError(
            f"Unknown model profile {profile_name!r}. Choose from: {available}"
        )

    agents = profile.get("agents") or {}
    if agent not in _AGENT_KEYS:
        raise ValueError(f"Unknown agent {agent!r}")

    agent_cfg = agents.get(agent)
    if not isinstance(agent_cfg, dict):
        raise ValueError(
            f"Profile {profile_name!r} has no config for agent {agent!r}"
        )

    model = str(agent_cfg.get("model", "")).strip()
    reasoning = str(agent_cfg.get("reasoning", "low")).strip() or "low"
    if not model:
        raise ValueError(
            f"Profile {profile_name!r} agent {agent!r} is missing model"
        )
    return {"model": model, "reasoning": reasoning}


def resolve_agent_model(agent: str) -> str:
    """Return the model id for an agent key (market, news, outlook, calendar, chief)."""
    env_key = _AGENT_MODEL_ENV[agent]
    override = os.getenv(env_key, "").strip()
    if override:
        return override
    profile_name = resolve_active_profile_name()
    return _agent_config_for_profile(profile_name, agent)["model"]


def resolve_reasoning_effort(agent: str) -> str:
    env_key = f"FR_REASONING_{agent.upper()}"
    override = os.getenv(env_key, "").strip()
    if override:
        return override
    profile_name = resolve_active_profile_name()
    return _agent_config_for_profile(profile_name, agent)["reasoning"]


def describe_active_profile() -> str:
    """Human-readable summary of the active profile and per-agent models."""
    profile_name = resolve_active_profile_name()
    parts = [f"{agent}={resolve_agent_model(agent)}" for agent in _AGENT_KEYS]
    return f"{profile_name} ({', '.join(parts)})"


def build_agent_llm(agent: str) -> LLM:
    """Construct a CrewAI LLM with model tier and reasoning effort for one agent."""
    return LLM(
        model=resolve_agent_model(agent),
        reasoning_effort=resolve_reasoning_effort(agent),
    )
