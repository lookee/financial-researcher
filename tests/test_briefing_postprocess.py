"""Tests for deterministic briefing post-processing."""

import json

from financial_researcher.services.briefing_postprocess import (
    calendar_table_normalization_warning,
    enforce_high_tag_cap,
    normalize_calendar_table,
    renumber_citations,
    validate_citations,
    validate_material_news_prominence,
)

MATERIAL_HIGH_DOMINANT = (
    "### STMicroelectronics N.V. (STMMI.MI) — Impact **HIGH**\n"
    "**Dominant watchlist story:** STM announces fab expansion.\n"
)

MATERIAL_HIGH_TWO = (
    "### Intesa Sanpaolo S.p.A. (ISP.MI) — Impact **HIGH**\n"
    "- headline\n\n"
    "### VanEck Semiconductor UCITS ETF (SMH.MI) — Impact **HIGH**\n"
    "- chip news\n\n"
    "### L&G Artificial Intelligence UCITS ETF (AIAI.MI) — Impact **MEDIUM**\n"
)

SAMPLE_OVER_TAGGED = """\
## Executive Summary

🔴 **HIGH — Intesa Sanpaolo S.p.A. (ISP.MI)** leads the day [7].
- 🔴 **HIGH — VanEck Semiconductor UCITS ETF (SMH.MI)** chip rally [8].
- 🔴 **HIGH — L&G Artificial Intelligence UCITS ETF (AIAI.MI)** AI theme [9].
- 🔴 **HIGH — iShares Quantum Computing UCITS ETF USD (Acc) (QOMP.DE)** quantum [10].
- 🔴 **HIGH — iShares MSCI China A UCITS ETF (36BZ.DE)** China [11].
- 🔴 **HIGH — iShares Edge MSCI World Quality Factor UCITS ETF USD (Acc) (IWQU.MI)** quality [12].
- 🔴 **HIGH — Extra tag** on another line [13].
- 🔴 **HIGH — Yet another** tag [14].
"""


class TestEnforceHighTagCap:
    def test_caps_eight_red_tags_to_two_high_instruments(self):
        result = enforce_high_tag_cap(SAMPLE_OVER_TAGGED, MATERIAL_HIGH_TWO)
        assert result.count("🔴") == 2
        assert "🔴 **HIGH — Intesa Sanpaolo S.p.A. (ISP.MI)**" in result
        assert "🔴 **HIGH — VanEck Semiconductor UCITS ETF (SMH.MI)**" in result
        assert "🔴" not in result.split("SMH.MI)** chip")[1]

    def test_leaves_content_when_at_most_two_tags(self):
        brief = "🔴 **HIGH — Intesa Sanpaolo S.p.A. (ISP.MI)** [7]\n🔴 opening [8]\n"
        material = "### Intesa Sanpaolo S.p.A. (ISP.MI) — Impact **HIGH**\n"
        assert enforce_high_tag_cap(brief, material) == brief


class TestRenumberCitations:
    def test_closes_gap_from_20_to_23(self):
        content = """\
Body cites [20] and [23] for research.

## References

20. Source A — title A — 2026-06-01 — https://example.com/a
23. Source B — title B — 2026-06-02 — https://example.com/b
"""
        seed_refs = {
            20: "Source A — title A — 2026-06-01 — https://example.com/a",
            23: "Source B — title B — 2026-06-02 — https://example.com/b",
        }
        updated, mapping = renumber_citations(content, instrument_count=6, seed_refs=seed_refs)
        assert mapping == {20: 7, 23: 8}
        assert "[20]" not in updated
        assert "[23]" not in updated
        assert "[7]" in updated
        assert "[8]" in updated
        assert "7. Source A" in updated
        assert "8. Source B" in updated
        assert "[1]" not in updated or "[6]" in updated  # market refs untouched if absent

    def test_preserves_market_citations(self):
        content = "Market [1] and research [20]."
        updated, mapping = renumber_citations(
            content,
            instrument_count=6,
            seed_refs={20: "Source — title — 2026-06-01 — https://example.com"},
        )
        assert "[1]" in updated
        assert mapping == {20: 7}


class TestNormalizeCalendarTable:
    def test_remaps_italian_headers(self):
        content = """\
## Calendario degli Eventi

| Data | Evento | Strumento | Impatto | Source |
|------|--------|-----------|---------|--------|
| 2026-06-15 | ECB meeting | SMH.MI | Central bank | [20] |
"""
        updated = normalize_calendar_table(content)
        assert "| Date (YYYY-MM-DD) | Event | Affected tickers/themes | Impact | [N] |" in updated
        assert "| 2026-06-15 | ECB meeting | SMH.MI | Central bank | [20] |" in updated

    def test_warning_when_headers_unmappable(self):
        content = """\
## Event Calendar

| Foo | Bar |
|---|---|
| 1 | 2 |
"""
        assert calendar_table_normalization_warning(content) is not None


class TestValidateCitations:
    def test_detects_research_numbering_gaps(self):
        warnings = validate_citations(
            "Facts [7] and [9] cited.",
            reference_count=9,
            instrument_count=6,
        )
        assert any("gaps" in warning for warning in warnings)


class TestValidateMaterialNewsProminence:
    def _seed(self, *, ticker: str, title: str, url: str) -> str:
        return json.dumps(
            [
                {
                    "citation": 7,
                    "ticker": ticker,
                    "title": title,
                    "url": url,
                    "source": "Borsa Italiana",
                    "date": "2026-06-12",
                }
            ]
        )

    def test_institutional_headline_present_no_warning(self):
        title = "STM announces new fab investment in Italy"
        content = f"Executive summary covers {title[:40]} with facts [7]."
        warnings = validate_material_news_prominence(
            content,
            {
                "watchlist_material_news": MATERIAL_HIGH_DOMINANT,
                "research_reference_seed_json": self._seed(
                    ticker="STMMI.MI",
                    title=title,
                    url="https://www.borsaitaliana.it/comunicati/example",
                ),
            },
        )
        assert warnings == []

    def test_institutional_headline_absent_warns_with_ticker(self):
        title = "STM announces new fab investment in Italy"
        warnings = validate_material_news_prominence(
            "Briefing discusses sector themes only.",
            {
                "watchlist_material_news": MATERIAL_HIGH_DOMINANT,
                "research_reference_seed_json": self._seed(
                    ticker="STMMI.MI",
                    title=title,
                    url="https://www.borsaitaliana.it/comunicati/example",
                ),
            },
        )
        assert len(warnings) == 1
        assert "STMMI.MI" in warnings[0]
        assert "institutional source" in warnings[0]

    def test_non_institutional_url_no_warning(self):
        title = "Chip stocks rally on AI demand"
        warnings = validate_material_news_prominence(
            "No mention of the prefetch headline.",
            {
                "watchlist_material_news": MATERIAL_HIGH_DOMINANT,
                "research_reference_seed_json": self._seed(
                    ticker="SMH.MI",
                    title=title,
                    url="https://www.reuters.com/markets/example",
                ),
            },
        )
        assert warnings == []

    def test_malformed_seed_json_no_crash(self):
        warnings = validate_material_news_prominence(
            "Any briefing body.",
            {
                "watchlist_material_news": MATERIAL_HIGH_DOMINANT,
                "research_reference_seed_json": "not-valid-json",
            },
        )
        assert warnings == []

    def test_empty_seed_json_no_warning(self):
        warnings = validate_material_news_prominence(
            "Any briefing body.",
            {
                "watchlist_material_news": MATERIAL_HIGH_DOMINANT,
                "research_reference_seed_json": "",
            },
        )
        assert warnings == []

    def test_vague_english_language_warning_when_dominant_high(self):
        warnings = validate_material_news_prominence(
            "Moves reflect sector uncertainty amid competition.",
            {"watchlist_material_news": MATERIAL_HIGH_DOMINANT},
        )
        assert len(warnings) == 1
        assert "vague sector/speculation language" in warnings[0]

    def test_vague_italian_language_warning_when_dominant_high(self):
        material = (
            "### STMicroelectronics N.V. (STMMI.MI) — Impact **HIGH**\n"
            "**Notizia dominante:** espansione del fab.\n"
        )
        warnings = validate_material_news_prominence(
            "Il titolo riflette speculazioni e incertezze nel settore.",
            {"watchlist_material_news": material},
        )
        assert len(warnings) == 1
        assert "vague sector/speculation language" in warnings[0]
