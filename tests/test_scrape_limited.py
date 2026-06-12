"""Tests for scrape text truncation."""

from financial_researcher.settings import get_scrape_settings
from financial_researcher.tools.scrape_limited import TRUNCATION_SUFFIX, truncate_scraped_text
from crewai_tools import ScrapeWebsiteTool


class TestTruncateScrapedText:
    def test_no_op_when_under_limit(self):
        text = "Short page content."
        assert truncate_scraped_text(text, max_chars=100) == text

    def test_prefers_keyword_paragraphs(self):
        text = (
            "Generic market overview " * 30 + "\n\n"
            "Intesa Sanpaolo launches OPAS on MPS with key regulatory facts.\n\n"
            "Footer links " * 30
        )
        result = truncate_scraped_text(
            text,
            max_chars=120,
            keywords=["intesa", "sanpaolo", "opas"],
        )
        assert TRUNCATION_SUFFIX in result
        assert "Intesa Sanpaolo" in result
        assert len(result) <= 120 + len(TRUNCATION_SUFFIX) + 2

    def test_falls_back_to_start_when_no_keyword_match(self):
        text = "Alpha paragraph.\n\n" + ("Beta filler " * 80)
        result = truncate_scraped_text(text, max_chars=80, keywords=["zzznomatch"])
        assert result.endswith(TRUNCATION_SUFFIX)
        assert result.startswith("Alpha")


class TestBuildScrapeTool:
    def test_returns_limited_tool_by_default(self, monkeypatch):
        monkeypatch.setattr(
            "financial_researcher.tools.scrape_limited.get_scrape_settings",
            lambda: {"truncate_enabled": True, "max_chars": 2500},
        )
        from financial_researcher.tools import scrape_limited

        tool = scrape_limited.build_scrape_tool()
        assert tool.__class__.__name__ == "LimitedScrapeWebsiteTool"
        assert tool.max_chars == 2500

    def test_returns_plain_tool_when_disabled(self, monkeypatch):
        monkeypatch.setattr(
            "financial_researcher.tools.scrape_limited.get_scrape_settings",
            lambda: {"truncate_enabled": False, "max_chars": 2500},
        )
        from financial_researcher.tools import scrape_limited

        tool = scrape_limited.build_scrape_tool()
        assert isinstance(tool, ScrapeWebsiteTool)
        assert tool.__class__.__name__ == "ScrapeWebsiteTool"


class TestScrapeSettings:
    def test_defaults_enabled(self):
        get_scrape_settings.cache_clear()
        settings = get_scrape_settings()
        assert settings["truncate_enabled"] is True
        assert settings["max_chars"] == 2500
