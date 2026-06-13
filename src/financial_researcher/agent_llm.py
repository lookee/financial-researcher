"""Per-agent LLM model and reasoning-effort configuration.

Profiles use {provider}_{tier} naming in defaults/model_profiles.yaml.
Free tiers are prefixed free_ (zero LLM cost).
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
_FALLBACK_DEFAULT_PROFILE = "openai_balanced"

_OPENROUTER_AUTO_MODELS = frozenset(
    {
        "openrouter/openrouter/auto",
        "openrouter/auto",
    }
)


def is_free_profile(profile_name: str | None = None) -> bool:
    """True for free_ profiles (zero LLM token cost)."""
    name = (profile_name or resolve_active_profile_name()).strip()
    return name.startswith("free_")


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
    from financial_researcher.settings import get_openrouter_auto_tradeoff_from_config

    get_openrouter_auto_tradeoff_from_config.cache_clear()


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


def is_openrouter_auto_model(model: str) -> bool:
    """True when the model id routes through OpenRouter Auto."""
    return model.strip().lower() in _OPENROUTER_AUTO_MODELS


def build_openrouter_auto_plugins(tradeoff: int) -> list[dict[str, Any]]:
    """OpenRouter Auto Router plugin payload for LiteLLM/CrewAI."""
    from financial_researcher.settings import clamp_openrouter_auto_tradeoff

    level = clamp_openrouter_auto_tradeoff(tradeoff)
    return [
        {
            "id": "auto-router",
            "cost_quality_tradeoff": level,
        }
    ]


def resolve_openrouter_auto_tradeoff() -> int | None:
    """Savings level 1–10 when OpenRouter Auto is in use, else None.

    Priority: OPENROUTER_AUTO_TRADEOFF (CLI/env) > settings.yaml openrouter.auto_tradeoff
    > profile auto_tradeoff > default 7.
    """
    if not uses_openrouter_auto_routing():
        return None

    from financial_researcher.settings import (
        get_openrouter_auto_tradeoff_from_config,
        parse_openrouter_auto_tradeoff,
    )

    configured = get_openrouter_auto_tradeoff_from_config()
    if configured is not None:
        return configured

    profile_name = resolve_active_profile_name()
    profile = (_load_profiles_document().get("profiles") or {}).get(profile_name) or {}
    if isinstance(profile, dict):
        profile_value = parse_openrouter_auto_tradeoff(profile.get("auto_tradeoff"))
        if profile_value is not None:
            return profile_value

    return 7


def uses_openrouter_auto_routing() -> bool:
    """True when any active agent model is OpenRouter Auto."""
    return any(is_openrouter_auto_model(resolve_agent_model(agent)) for agent in _AGENT_KEYS)


def _agent_config_for_profile(profile_name: str, agent: str) -> dict[str, str]:
    profile_name = profile_name.strip()
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
    prefix = "[FREE] " if is_free_profile(profile_name) else ""
    summary = f"{prefix}{profile_name} ({', '.join(parts)})"
    if uses_openrouter_auto_routing():
        tradeoff = resolve_openrouter_auto_tradeoff()
        if tradeoff is not None:
            summary += f" | openrouter_savings={tradeoff}/10"
    return summary


def build_agent_llm(agent: str) -> LLM:
    """Construct a CrewAI LLM with model tier and reasoning effort for one agent."""
    model = resolve_agent_model(agent)
    llm_kwargs: dict[str, Any] = {
        "model": model,
        "reasoning_effort": resolve_reasoning_effort(agent),
    }
    if is_openrouter_auto_model(model):
        tradeoff = resolve_openrouter_auto_tradeoff()
        if tradeoff is not None:
            llm_kwargs["plugins"] = build_openrouter_auto_plugins(tradeoff)
    return LLM(**llm_kwargs)
