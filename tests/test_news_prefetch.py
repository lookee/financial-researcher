"""Tests for material news brief generation."""

from financial_researcher.services.news_prefetch import build_material_news_brief


def _etf_item() -> dict:
    return {
        "citation": 1,
        "name": "VanEck Semiconductor UCITS ETF",
        "ticker": "SMH.MI",
        "type": "etf",
        "performance": {"1d": 2.94, "ytd": 73.89},
    }


def _stock_item() -> dict:
    return {
        "citation": 2,
        "name": "Intesa Sanpaolo S.p.A.",
        "ticker": "ISP.MI",
        "type": "stock",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "performance": {"1d": 0.07, "ytd": -2.77},
    }


class TestBuildMaterialNewsBrief:
    def test_reference_page_only_emits_none_impact(self):
        reference = {
            "date": "2026-01-01",
            "title": "VanEck Semiconductor UCITS ETF company profile",
            "source": "justETF",
            "url": "https://www.justetf.com/en/etf-profile.html?isin=IE00BMC38736",
            "summary": "Holdings and performance recap",
            "region": "Serper global",
        }
        brief = build_material_news_brief(
            [_etf_item()],
            {"SMH.MI": [reference]},
            language="English",
        )
        assert "Impact **NONE**" in brief
        assert "do NOT cite profile/fact-sheet pages" in brief
        assert "1D: 2.94%" in brief
        assert "YTD: 73.89%" in brief
        assert "[1]" in brief
        assert "Headline to report" not in brief
        assert "Dominant watchlist story" not in brief

    def test_material_news_unchanged(self):
        news = {
            "date": "2026-06-11",
            "title": "Intesa Sanpaolo, Messina: pronti a rispondere a qualsiasi controfferta per MPS",
            "source": "Borsa Italiana",
            "url": (
                "https://www.borsaitaliana.it/borsa/notizie/teleborsa/finanza/"
                "intesa-sanpaolo-messina-pronti-a-rispondere-a-qualsiasi-controfferta-per-mps.html"
            ),
            "summary": "Banking M&A update",
            "region": "Serper IT issuer",
            "issuer_event": "1",
        }
        brief = build_material_news_brief(
            [_stock_item()],
            {"ISP.MI": [news]},
            language="Italian",
        )
        assert "Impact **NONE**" not in brief
        assert "Impact **" in brief
        assert "**Titolo da riportare**" in brief
        assert "controfferta per MPS" in brief

    def test_none_instruments_excluded_from_dominant_story(self):
        reference = {
            "date": "n/a",
            "title": "ETF holdings and performance recap",
            "source": "extraETF",
            "url": "https://extraetf.com/en/etf-profile/IE00BK5BCD43",
            "summary": "",
            "region": "Serper global",
        }
        news = {
            "date": "2026-06-11",
            "title": "Intesa Sanpaolo detiene il 3,127% in Generali (Consob)",
            "source": "Borsa Italiana",
            "url": (
                "https://www.borsaitaliana.it/borsa/notizie/teleborsa/finanza/"
                "generali-intesa-sanpaolo-detiene-il-3127-consob.html"
            ),
            "summary": "Regulatory disclosure",
            "region": "Serper IT issuer",
            "issuer_event": "1",
        }
        brief = build_material_news_brief(
            [_etf_item(), _stock_item()],
            {"SMH.MI": [reference], "ISP.MI": [news]},
            language="English",
        )
        assert brief.count("Impact **NONE**") == 1
        assert "Dominant watchlist story" in brief
        dominant_line = next(
            line for line in brief.splitlines() if line.startswith("**Dominant watchlist story")
        )
        assert "Intesa Sanpaolo" in dominant_line
        assert "VanEck" not in dominant_line
