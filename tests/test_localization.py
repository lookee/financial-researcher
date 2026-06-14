"""Tests for English labels in localization.py."""

from financial_researcher.localization import (
    agent_labels,
    english_section_headings,
    is_italian_language,
    label,
    run_metadata_copy,
    section_alias_map,
    section_heading,
    section_title_variants,
)


class TestSectionHeadings:
    def test_headings_always_english(self):
        assert section_heading("executive_summary", language="English") == (
            "Executive Summary"
        )
        assert section_heading("drivers", language="Italian") == "What's Driving the Moves"

    def test_aliases_include_legacy_italian_titles(self):
        aliases = section_alias_map()
        assert aliases["sommario esecutivo"] == "executive_summary"
        assert aliases["cosa guida i movimenti"] == "drivers"

    def test_section_title_variants_cover_aliases(self):
        variants = section_title_variants("performance")
        assert "watchlist performance snapshot" in variants
        assert "snapshot della performance watchlist" in variants

    def test_english_section_headings_matches_order(self):
        headings = english_section_headings()
        assert headings["references"] == "References"
        assert "disclaimer" in headings


class TestLabels:
    def test_run_metadata_labels(self):
        assert run_metadata_copy()["heading"] == "Run metadata"

    def test_chart_heading(self):
        assert label("charts", "performance_charts") == "Performance Charts"

    def test_agent_labels(self):
        assert agent_labels()["chief"] == "Chief strategist"

    def test_is_italian_language_for_body_only(self):
        assert is_italian_language("Italian")
        assert not is_italian_language("English")
