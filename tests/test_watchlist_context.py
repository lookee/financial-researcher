"""Tests for watchlist context table builders."""

from financial_researcher.services.briefing_postprocess import _replace_section_body
from financial_researcher.services.market_data import compute_volatility_30d
from financial_researcher.services.watchlist_context import (
    build_market_pulse_table,
    build_watchlist_performance_table,
)
import pandas as pd


def _sample_instrument(**overrides) -> dict:
    base = {
        "citation": 1,
        "name": "Example ETF",
        "ticker": "EX.MI",
        "type": "etf",
        "currency": "EUR",
        "price": {"last": 23.45},
        "performance": {"1d": 1.2, "1w": -0.5, "1m": 11.48, "1y": 5.0, "ytd": 4.0},
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
        assert "1,20%" in table
        assert "11. 48%" not in table  # no thousand-separator artifact
        assert "11,48%" in table
        assert "[1] ⚠" in table

    def test_includes_ytd_1y_and_vol_columns(self):
        table = build_watchlist_performance_table(
            [_sample_instrument(volatility_30d=12.34)],
            language="English",
        )
        assert "| YTD | 1Y |" in table
        assert "30d Vol" in table
        assert "4.00%" in table
        assert "12.34%" in table

    def test_benchmark_rows_appended(self):
        benchmark = {
            "ticker": "FTSEMIB.MI",
            "name": "FTSE MIB",
            "price": {"current": 35000},
            "performance": {"1d": 0.5, "1w": 1.0, "1m": 2.0, "ytd": 3.0, "1y": 4.0},
            "source_url": "https://finance.yahoo.com/quote/FTSEMIB.MI",
        }
        table = build_watchlist_performance_table(
            [_sample_instrument()],
            benchmarks=[benchmark],
        )
        assert "FTSE MIB" in table
        assert "FTSEMIB.MI" in table
        assert table.strip().splitlines()[-1].startswith("| — |")


class TestComputeVolatility30d:
    def test_returns_percentage_for_sufficient_history(self):
        closes = [100 + i for i in range(40)]
        history = pd.DataFrame({"Close": closes})
        vol = compute_volatility_30d(history)
        assert vol is not None
        assert vol > 0


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
