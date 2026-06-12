"""Tests for publication date normalization and freshness roles."""

from datetime import date

from financial_researcher.services.source_freshness import (
    annotate_headline_freshness,
    freshness_role,
    normalize_publication_date,
)


class TestNormalizePublicationDate:
    def test_iso_date(self):
        assert normalize_publication_date("2026-06-11") == "2026-06-11"

    def test_relative_italian(self):
        assert normalize_publication_date(
            "1 giorno fa", as_of=date(2026, 6, 12)
        ) == "2026-06-11"


class TestFreshnessRole:
    def test_recent_is_causal(self):
        assert freshness_role("2026-06-11", as_of=date(2026, 6, 12)) == "causal"

    def test_old_is_background(self):
        assert freshness_role("2026-05-01", as_of=date(2026, 6, 12)) == "background"


class TestAnnotateHeadline:
    def test_adds_fields(self):
        enriched = annotate_headline_freshness(
            {"date": "1 giorno fa", "title": "News"},
            as_of=date(2026, 6, 12),
        )
        assert enriched["published_date"] == "2026-06-11"
        assert enriched["freshness_role"] == "causal"
        assert "CAUSAL" in enriched["freshness_label"]
