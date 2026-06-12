"""Tests for watchlist context table builders."""

from financial_researcher.services.briefing_postprocess import _replace_section_body
from financial_researcher.services.watchlist_context import (
    build_market_pulse_table,
    build_watchlist_performance_table,
)


def _sample_instrument(**overrides) -> dict:
    base = {
        "citation": 1,
        "name": "Example ETF",
        "ticker": "EX.MI",
        "type": "etf",
        "currency": "EUR",
        "price": {"last": 23.45},
        "performance": {"1d": 1.2, "1w": -0.5, "1m": 3.0, "1y": 5.0, "ytd": 4.0},
    }
    base.update(overrides)
    return base


class TestBuildWatchlistPerformanceTable:
    def test_single_source_ref_and_price_column_en(self):
        table = build_watchlist_performance_table([_sample_instrument()], language="English")
        assert "| Price (ccy) |" in table
        assert "| Source |" in table
        assert "23.45 EUR" in table
        assert table.count("[1]") == 2  # Ref column + Source column only
        assert "1.20% [1]" not in table

    def test_italian_price_format_and_source_warning(self):
        table = build_watchlist_performance_table(
            [_sample_instrument(quality_flags=["1d_inconsistent"])],
            language="Italian",
        )
        assert "Prezzo (valuta)" in table
        assert "23,45 EUR" in table
        assert "[1] ⚠" in table


class TestBuildMarketPulseTable:
    def test_ref_only_in_first_column(self):
        table = build_market_pulse_table([_sample_instrument()])
        assert table.count("[1]") == 1
        assert "1.20% [1]" not in table


class TestReplaceSectionBodyWithPerformanceTable:
    def test_injects_new_table_format(self):
        content = """\
# Title

## Executive Summary

Summary text.

## Watchlist Performance Snapshot

Old leader line.

| old | table |

## What's Driving the Moves

Drivers.
"""
        new_body = "**1D leader:** Example ETF (EX.MI) (1.20%)\n\n" + build_watchlist_performance_table(
            [_sample_instrument()], language="English"
        )
        updated = _replace_section_body(
            content,
            title_keys={"watchlist performance snapshot"},
            new_body=new_body,
        )
        assert "| Price (ccy) |" in updated
        assert "| old | table |" not in updated
        assert "## What's Driving the Moves" in updated
