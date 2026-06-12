"""Tests for Serper query sanitisation."""

from financial_researcher.tools.serper_query import sanitize_serper_query


class TestSanitizeSerperQuery:
    def test_strips_site_operator(self):
        raw = '"Intesa Sanpaolo" OR ISP.MI site:borsaitaliana.it'
        assert sanitize_serper_query(raw) == "Intesa Sanpaolo"

    def test_simplifies_or_chain_to_first_quoted_phrase(self):
        raw = (
            '"VanEck Semiconductor UCITS ETF" OR SMH.MI '
            "Reuters OR Bloomberg OR CNBC 2026"
        )
        assert sanitize_serper_query(raw) == "VanEck Semiconductor UCITS ETF"

    def test_unchanged_when_free_tier_disabled(self):
        raw = "NVDA site:nasdaq.com"
        assert sanitize_serper_query(raw, free_tier=False) == raw
