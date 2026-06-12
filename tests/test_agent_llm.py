"""Tests for per-agent model and reasoning-effort configuration."""

import os

from financial_researcher.agent_llm import (
    _DEFAULT_MODELS,
    _REASONING_EFFORT,
    build_agent_llm,
    resolve_agent_model,
    resolve_reasoning_effort,
)


def test_default_models_match_cost_tier_plan():
    assert resolve_agent_model("market") == "openai/gpt-5.4-mini"
    assert resolve_agent_model("news") == "openai/gpt-5.5"
    assert resolve_agent_model("outlook") == "openai/gpt-5.4"
    assert resolve_agent_model("calendar") == "openai/gpt-5.4-mini"
    assert resolve_agent_model("chief") == "openai/gpt-5.5"


def test_model_override_via_env(monkeypatch):
    monkeypatch.setenv("FR_MODEL_OUTLOOK", "openai/gpt-5.5")
    assert resolve_agent_model("outlook") == "openai/gpt-5.5"
    monkeypatch.delenv("FR_MODEL_OUTLOOK", raising=False)
    assert resolve_agent_model("outlook") == _DEFAULT_MODELS["outlook"]


def test_reasoning_effort_tiers():
    assert resolve_reasoning_effort("market") == "low"
    assert resolve_reasoning_effort("calendar") == "low"
    assert resolve_reasoning_effort("outlook") == "low"
    assert resolve_reasoning_effort("news") == "medium"
    assert resolve_reasoning_effort("chief") == "medium"


def test_build_agent_llm_sets_model_and_reasoning(monkeypatch):
    monkeypatch.delenv("FR_MODEL_MARKET", raising=False)
    llm = build_agent_llm("market")
    assert llm.model == "openai/gpt-5.4-mini"
    assert llm.reasoning_effort == _REASONING_EFFORT["market"]
