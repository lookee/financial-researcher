"""Tests for settings.yaml and environment resolution."""

import pytest

from financial_researcher.settings import (
    _load_yaml_settings,
    get_benchmark_settings,
    get_default_language,
    get_model_profile_name,
    get_pipeline_settings,
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
    yield
    _load_yaml_settings.cache_clear()
    get_scrape_settings.cache_clear()
    get_serper_settings.cache_clear()
    get_pipeline_settings.cache_clear()
    get_benchmark_settings.cache_clear()


def test_model_profile_name_defaults_to_balanced(monkeypatch):
    monkeypatch.delenv("FR_MODEL_PROFILE", raising=False)
    assert get_model_profile_name() == "balanced"


def test_model_profile_name_from_env(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "deepseek")
    assert get_model_profile_name() == "deepseek"


def test_model_profile_name_env_beats_yaml(monkeypatch):
    monkeypatch.setenv("FR_MODEL_PROFILE", "multi")
    assert get_model_profile_name() == "multi"


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
