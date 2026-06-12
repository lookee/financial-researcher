"""Tests for crew wiring and watchlist context inputs."""

from pathlib import Path

import yaml

from financial_researcher.services.watchlist_context import build_watchlist_context
from financial_researcher.models.instrument import InstrumentIdentity


def test_watchlist_context_omits_redundant_news_query_blocks():
    identity = InstrumentIdentity(
        isin="IT0000072618",
        name="Intesa Sanpaolo S.p.A.",
        primary_ticker="ISP.MI",
        instrument_type="stock",
        exchange="MIL",
        currency="EUR",
    )
    snapshot = {
        "source_url": "https://finance.yahoo.com/quote/ISP.MI",
        "price": {"current": 5.6, "previous_close": 5.59, "currency": "EUR", "change_percent": 0.07},
        "performance": {"1d": 0.07, "1w": -1.6, "1m": 1.34, "3m": 8.83, "ytd": -2.77, "1y": 22.49},
        "profile": {"sector": "Financial Services", "industry": "Banks - Regional", "market_cap": 1},
        "fundamentals": {"pe_ratio": 10.0},
        "forecasts": None,
    }
    inputs = build_watchlist_context([identity], [snapshot], session="close", language="English")
    assert "stock_news_queries" not in inputs
    assert "etf_news_queries" not in inputs
    assert "prefetched_news_digest" not in inputs


def test_news_task_template_has_no_mandatory_query_placeholders():
    tasks_path = Path(__file__).parents[1] / "src/financial_researcher/defaults/tasks_briefing.yaml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    description = tasks["news_analysis_task"]["description"]
    assert "{stock_news_queries}" not in description
    assert "{etf_news_queries}" not in description
    assert "Hard cap: 4 tool calls per instrument, 12 per run" in description


def test_news_analyst_yaml_has_prefetch_first_workflow():
    agents_path = Path(__file__).parents[1] / "src/financial_researcher/defaults/agents_briefing.yaml"
    agents = yaml.safe_load(agents_path.read_text(encoding="utf-8"))
    instructions = agents["news_analyst"]["instructions"]
    assert "stock_news_queries" not in instructions
    assert "YahooFinanceNewsTool" not in instructions
    assert "12 per run" in instructions


def test_analyst_tasks_have_word_caps():
    tasks_path = Path(__file__).parents[1] / "src/financial_researcher/defaults/tasks_briefing.yaml"
    tasks = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    assert "≤300 words" in tasks["market_analysis_task"]["description"]
    assert "≤450 words" in tasks["news_analysis_task"]["description"]
    assert "≤350 words" in tasks["outlook_analysis_task"]["description"]
    assert "≤250 words" in tasks["calendar_analysis_task"]["description"]


def test_agent_yaml_has_no_dynamic_placeholders():
    agents_path = Path(__file__).parents[1] / "src/financial_researcher/defaults/agents_briefing.yaml"
    text = agents_path.read_text(encoding="utf-8")
    assert "{current_date}" not in text
    assert "{session_label}" not in text
    assert "llm:" not in text
