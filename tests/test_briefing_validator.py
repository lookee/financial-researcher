"""Tests for post-generation briefing validation."""

from financial_researcher.services.briefing_validator import (
    format_validation_summary,
    validate_briefing,
    validate_section_language,
)


def _inputs(instruments):
    return {
        "language": "Italian",
        "watchlist_instruments_json": __import__("json").dumps(instruments),
        "watchlist_context": '{"language": "Italian", "instruments": []}',
    }


class TestValidateSectionLanguage:
    def test_detects_duplicate_performance_sections(self):
        content = """\
## Executive Summary
A
## Watchlist Performance Snapshot
B
## Watchlist Performance Snapshot
C
"""
        warnings = validate_section_language(content, language="Italian")
        assert any("Duplicate section" in w for w in warnings)


class TestValidateBriefing:
    def test_ok_when_citations_match(self):
        content = """\
## Sommario Esecutivo
Move +1,20% 1D [1].

## Riferimenti

1. Yahoo Finance — EX.MI — 2026-06-12 — https://example.com
"""
        instruments = [
            {
                "citation": 1,
                "name": "Example",
                "ticker": "EX.MI",
                "performance": {"1d": 1.2},
            }
        ]
        warnings = validate_briefing(content, _inputs(instruments))
        assert format_validation_summary(warnings) == "Validation: OK (0 warnings)"
