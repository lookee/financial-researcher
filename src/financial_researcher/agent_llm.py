"""Per-agent LLM model and reasoning-effort configuration.

Models are overridable via environment variables so an all-frontier lineup is a
config change, not a code change. Reasoning effort is set per agent because
reasoning tokens bill as output — analysts summarising pre-computed data need
less chain-of-thought than news synthesis and the final memo.
"""

from __future__ import annotations

import os

from crewai import LLM

_AGENT_MODEL_ENV: dict[str, str] = {
    "market": "FR_MODEL_MARKET",
    "news": "FR_MODEL_NEWS",
    "outlook": "FR_MODEL_OUTLOOK",
    "calendar": "FR_MODEL_CALENDAR",
    "chief": "FR_MODEL_CHIEF",
}

_DEFAULT_MODELS: dict[str, str] = {
    "market": "openai/gpt-5.4-mini",
    "news": "openai/gpt-5.5",
    "outlook": "openai/gpt-5.4",
    "calendar": "openai/gpt-5.4-mini",
    "chief": "openai/gpt-5.5",
}

# low = market/calendar/outlook (table fill or search summarisation);
# medium = news + chief (multi-source synthesis and executive prose).
_REASONING_EFFORT: dict[str, str] = {
    "market": "low",
    "news": "medium",
    "outlook": "low",
    "calendar": "low",
    "chief": "medium",
}


def resolve_agent_model(agent: str) -> str:
    """Return the model id for an agent key (market, news, outlook, calendar, chief)."""
    env_key = _AGENT_MODEL_ENV[agent]
    override = os.getenv(env_key, "").strip()
    if override:
        return override
    return _DEFAULT_MODELS[agent]


def resolve_reasoning_effort(agent: str) -> str:
    return _REASONING_EFFORT[agent]


def build_agent_llm(agent: str) -> LLM:
    """Construct a CrewAI LLM with model tier and reasoning effort for one agent."""
    return LLM(
        model=resolve_agent_model(agent),
        reasoning_effort=resolve_reasoning_effort(agent),
    )
