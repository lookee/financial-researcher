"""Tests for settings.yaml and environment resolution."""

import pytest

from financial_researcher.agent_llm import clear_profile_caches, resolve_openrouter_auto_tradeoff
from financial_researcher.settings import (
    _load_yaml_settings,
    email_delivery_configured,
    get_benchmark_settings,
    get_default_language,
    get_email_settings,
    get_model_profile_name,
    get_pipeline_settings,
    get_openrouter_auto_tradeoff_from_config,
    get_report_settings,
    get_scrape_settings,
    get_serper_settings,
)


@pytest.fixture(autouse=True)
def _clear_settings_caches():
    _load_yaml_settings.cache_clear()
    get_scrape_settings.cache_clear()
    get_serper_settings.cache_clear()
    get_pipeline_settings.cache_clear()
    get_benchmark_settings.cache_clear()
    get_email_settings.cache_clear()
    get_report_settings.cache_clear()
    get_openrouter_auto_tradeoff_from_config.cache_clear()
    yield
    _load_yaml_settings.cache_clear()
    get_scrape_settings.cache_clear()
    get_serper_settings.cache_clear()
    get_pipeline_settings.cache_clear()
    get_benchmark_settings.cache_clear()
    get_email_settings.cache_clear()
    get_report_settings.cache_clear()
    get_openrouter_auto_tradeoff_from_config.cache_clear()


def test_model_profile_name_defaults_to_balanced(monkeypatch):
    monkeypatch.delenv("FR_MODEL_PROFILE", raising=False)
    assert get_model_profile_name() == "openai_balanced"


def test_model_profile_name_from_env(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "deepseek_balanced")
    assert get_model_profile_name() == "deepseek_balanced"


def test_model_profile_name_env_beats_yaml(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "mixed_balanced")
    assert get_model_profile_name() == "mixed_balanced"


def test_default_language_from_env(monkeypatch):
    monkeypatch.setenv("REPORT_LANGUAGE", "Italian")
    assert get_default_language() == "Italian"


def test_default_language_falls_back_to_packaged_default(monkeypatch):
    monkeypatch.delenv("REPORT_LANGUAGE", raising=False)
    assert get_default_language() == "English"


def test_scrape_settings_defaults():
    settings = get_scrape_settings()
    assert settings["truncate_enabled"] is True
    assert settings["max_chars"] == 2500


def test_scrape_settings_clamps_max_chars(monkeypatch):
    monkeypatch.setattr(
        "financial_researcher.settings._load_yaml_settings",
        lambda: {"scrape": {"max_chars": 99_999, "truncate_enabled": False}},
    )
    get_scrape_settings.cache_clear()
    settings = get_scrape_settings()
    assert settings["max_chars"] == 20_000
    assert settings["truncate_enabled"] is False


def test_serper_free_tier_env_override(monkeypatch):
    monkeypatch.setenv("SERPER_FREE_TIER", "false")
    assert get_serper_settings()["free_tier"] is False


def test_serper_free_tier_defaults_true(monkeypatch):
    monkeypatch.delenv("SERPER_FREE_TIER", raising=False)
    assert get_serper_settings()["free_tier"] is True


def test_pipeline_max_workers_clamped(monkeypatch):
    monkeypatch.setattr(
        "financial_researcher.settings._load_yaml_settings",
        lambda: {"pipeline": {"max_workers": 99}},
    )
    get_pipeline_settings.cache_clear()
    assert get_pipeline_settings()["max_workers"] == 16


def test_benchmark_settings_include_mib_and_stoxx():
    tickers = {b["ticker"] for b in get_benchmark_settings()}
    assert "FTSEMIB.MI" in tickers
    assert "^STOXX" in tickers


def test_email_settings_from_env(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("BRIEFING_EMAIL_FROM", "FR <from@example.com>")
    monkeypatch.setenv("BRIEFING_EMAIL_TO", "a@example.com, b@example.com")
    monkeypatch.setenv("BRIEFING_EMAIL_AUTO", "1")
    cfg = get_email_settings()
    assert cfg["api_key"] == "re_test"
    assert cfg["from_address"] == "FR <from@example.com>"
    assert cfg["to_addresses"] == ["a@example.com", "b@example.com"]
    assert cfg["auto_send"] is True
    assert email_delivery_configured() is True


def test_email_delivery_not_configured_without_recipient(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.delenv("BRIEFING_EMAIL_TO", raising=False)
    monkeypatch.delenv("BRIEFING_EMAIL_FROM", raising=False)
    assert email_delivery_configured() is False


def test_report_metadata_enabled_by_default(monkeypatch):
    monkeypatch.delenv("BRIEFING_RUN_METADATA", raising=False)
    assert get_report_settings()["include_run_metadata"] is True


def test_report_metadata_disabled_via_env(monkeypatch):
    monkeypatch.setenv("BRIEFING_RUN_METADATA", "0")
    assert get_report_settings()["include_run_metadata"] is False


def test_openrouter_tradeoff_env_overrides_profile(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "openrouter_auto_economy")
    monkeypatch.setenv("OPENROUTER_AUTO_TRADEOFF", "3")
    clear_profile_caches()
    assert resolve_openrouter_auto_tradeoff() == 3


def test_openrouter_tradeoff_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_AUTO_TRADEOFF", "9")
    get_openrouter_auto_tradeoff_from_config.cache_clear()
    assert get_openrouter_auto_tradeoff_from_config() == 9


def test_openrouter_tradeoff_clamped(monkeypatch):
    monkeypatch.setenv("OPENROUTER_AUTO_TRADEOFF", "99")
    get_openrouter_auto_tradeoff_from_config.cache_clear()
    assert get_openrouter_auto_tradeoff_from_config() == 10
