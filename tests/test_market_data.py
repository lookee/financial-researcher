"""Tests for canonical 1D performance calculation."""

from financial_researcher.services.market_data import compute_canonical_1d
from financial_researcher.services.watchlist_context import build_market_pulse_table


class TestComputeCanonical1d:
    def test_from_quote_when_both_prices_present(self):
        value, flags = compute_canonical_1d(103.0, 100.0, 2.8)
        assert value == 3.0
        assert flags == []

    def test_fallback_to_history_when_quote_missing(self):
        value, flags = compute_canonical_1d(None, 100.0, 1.25)
        assert value == 1.25
        assert flags == []

    def test_fallback_when_previous_close_zero(self):
        value, flags = compute_canonical_1d(50.0, 0.0, -0.8)
        assert value == -0.8
        assert flags == []

    def test_flags_when_quote_and_history_diverge(self):
        value, flags = compute_canonical_1d(105.0, 100.0, 1.0)
        assert value == 5.0
        assert flags == ["1d_inconsistent"]

    def test_no_flag_when_divergence_within_threshold(self):
        value, flags = compute_canonical_1d(101.4, 100.0, 1.0)
        assert value == 1.4
        assert flags == []


class TestMarketPulseTableQualityFlags:
    def test_appends_warning_on_inconsistent_1d(self):
        instruments = [
            {
                "citation": 1,
                "name": "Example ETF",
                "ticker": "EX.MI",
                "type": "etf",
                "currency": "EUR",
                "price": {"last": 10.0},
                "performance": {"1d": 2.5, "1w": 1.0, "1m": 3.0, "1y": 5.0, "ytd": 4.0},
                "quality_flags": ["1d_inconsistent"],
            }
        ]
        table = build_market_pulse_table(instruments)
        assert "2.50% ⚠" in table

    def test_no_warning_without_quality_flag(self):
        instruments = [
            {
                "citation": 1,
                "name": "Example ETF",
                "ticker": "EX.MI",
                "type": "etf",
                "currency": "EUR",
                "price": {"last": 10.0},
                "performance": {"1d": 2.5, "1w": 1.0, "1m": 3.0, "1y": 5.0, "ytd": 4.0},
            }
        ]
        table = build_market_pulse_table(instruments)
        assert "⚠" not in table
