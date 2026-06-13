"""Build aggregated watchlist context for the briefing crew."""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from financial_researcher.models.instrument import InstrumentIdentity
from financial_researcher.services.forward_calendar import (
    build_forward_calendar_table,
    build_recent_dated_events_table,
    fetch_forward_calendar_events,
)
from financial_researcher.session_profiles import resolve_session_profile
from financial_researcher.settings import get_default_language

BRIEFING_SECTION_ORDER = [
    "executive_summary",
    "performance",
    "drivers",
    "outlook",
    "calendar",
    "themes",
    "risks",
    "references",
    "disclaimer",
]

BRIEFING_SECTION_HEADINGS_EN: dict[str, str] = {
    "executive_summary": "Executive Summary",
    "performance": "Watchlist Performance Snapshot",
    "drivers": "What's Driving the Moves",
    "outlook": "Medium-Term Outlook",
    "calendar": "Event Calendar",
    "themes": "Correlated Themes",
    "risks": "Risks & Watchpoints",
    "references": "References",
    "disclaimer": "Disclaimer",
}

BRIEFING_SECTION_HEADINGS_IT: dict[str, str] = {
    "executive_summary": "Sommario Esecutivo",
    "performance": "Snapshot della Performance Watchlist",
    "drivers": "Cosa Guida i Movimenti",
    "outlook": "Prospettive di Medio Termine",
    "calendar": "Calendario Eventi",
    "themes": "Temi Correlati",
    "risks": "Rischi e Punti di Attenzione",
    "references": "Riferimenti",
    "disclaimer": "Disclaimer",
}


def is_italian_language(language: str) -> bool:
    return language.lower().startswith("ital")


def localized_section_heading(section_key: str, language: str) -> str:
    """Single localized ## heading for a briefing section key."""
    if is_italian_language(language):
        return BRIEFING_SECTION_HEADINGS_IT[section_key]
    return BRIEFING_SECTION_HEADINGS_EN[section_key]

MILAN_TZ = ZoneInfo("Europe/Rome")
SESSIONS_PATH = Path(__file__).parent.parent / "defaults" / "sessions_milan.yaml"

SESSION_LABELS = {
    "pre_open": "Pre-open (Milan)",
    "post_open": "Post-open (Milan)",
    "midday": "Midday (Milan)",
    "close": "Close (Milan)",
}


def _fmt_num(value: float | int | None, decimals: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.{decimals}f}"


def _fmt_pct(value: float | None, *, italian: bool = False) -> str:
    if value is None:
        return "n/a"
    if italian:
        return f"{value:.2f}".replace(".", ",") + "%"
    return f"{value:.2f}%"


def _fmt_price(
    value: float | int | None,
    currency: str,
    *,
    italian: bool,
) -> str:
    if value is None:
        return "n/a"
    if italian:
        body = f"{float(value):.2f}".replace(".", ",")
    else:
        body = f"{float(value):,.2f}"
    return f"{body} {currency}".strip() if currency else body


def instrument_label(item: dict[str, Any]) -> str:
    """Preferred prose reference: full name plus ticker."""
    return f"{item['name']} ({item['ticker']})"


def build_instrument_naming_guide(instruments: list[dict[str, Any]]) -> str:
    """Tell agents to cite instruments as Name (TICKER), never ticker alone in prose."""
    lines = [
        "Instrument naming in narrative text — use Name (TICKER) every time:",
        "Do NOT refer to an instrument by ticker alone in sentences or bullets.",
        "",
    ]
    for item in instruments:
        lines.append(f"- {instrument_label(item)}")
    return "\n".join(lines)


def _profile_label(
    identity: InstrumentIdentity,
    profile: dict[str, Any],
    fundamentals: dict[str, Any],
) -> str:
    """Infer a short profile label from resolved market data."""
    if identity.instrument_type == "etf":
        return fundamentals.get("category") or identity.name
    parts = [profile.get("sector"), profile.get("industry")]
    return " / ".join(part for part in parts if part) or identity.name


def _instrument_entry(
    identity: InstrumentIdentity,
    snapshot: dict[str, Any],
    citation: int,
) -> dict[str, Any]:
    price = snapshot.get("price", {})
    perf = snapshot.get("performance", {})
    profile = snapshot.get("profile", {})
    fundamentals = snapshot.get("fundamentals", {})
    forecasts = snapshot.get("forecasts")

    entry: dict[str, Any] = {
        "citation": citation,
        "isin": identity.isin,
        "name": identity.name,
        "ticker": identity.primary_ticker,
        "type": identity.instrument_type,
        "exchange": identity.exchange,
        "currency": price.get("currency") or identity.currency,
        "source_url": snapshot.get("source_url"),
        "price": {
            "last": price.get("current"),
            "change_1d_pct": price.get("change_percent"),
            "previous_close": price.get("previous_close"),
        },
        "performance": {
            "1d": perf.get("1d"),
            "1w": perf.get("1w"),
            "1m": perf.get("1m"),
            "3m": perf.get("3m"),
            "ytd": perf.get("ytd"),
            "1y": perf.get("1y"),
        },
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "profile": _profile_label(identity, profile, fundamentals),
    }

    if identity.instrument_type == "etf":
        entry["etf"] = {
            "aum": fundamentals.get("aum"),
            "category": fundamentals.get("category"),
            "fund_family": fundamentals.get("fund_family"),
        }
    else:
        entry["stock"] = {
            "market_cap": profile.get("market_cap"),
            "pe_ratio": fundamentals.get("pe_ratio"),
        }
        if forecasts:
            entry["forecasts"] = forecasts

    quality_flags = snapshot.get("quality_flags") or []
    if quality_flags:
        entry["quality_flags"] = list(quality_flags)

    vol = snapshot.get("volatility_30d")
    if vol is not None:
        entry["volatility_30d"] = vol

    history = snapshot.get("history")
    if history:
        entry["history"] = history

    return entry


def _slim_instrument_for_context(item: dict[str, Any]) -> dict[str, Any]:
    """Drop fields already present in market_pulse_table to save tokens."""
    slim: dict[str, Any] = {
        "citation": item["citation"],
        "name": item["name"],
        "ticker": item["ticker"],
        "type": item["type"],
        "profile": item.get("profile"),
        "sector": item.get("sector"),
        "industry": item.get("industry"),
    }
    if item.get("etf"):
        slim["etf"] = item["etf"]
    if item.get("stock"):
        slim["stock"] = item["stock"]
    if item.get("forecasts"):
        slim["forecasts"] = item["forecasts"]
    if item.get("quality_flags"):
        slim["quality_flags"] = item["quality_flags"]
    return slim


def _benchmark_table_row(
    snapshot: dict[str, Any],
    *,
    italian: bool,
) -> dict[str, Any]:
    perf = snapshot.get("performance", {})
    price = snapshot.get("price", {})
    return {
        "citation": "—",
        "name": snapshot.get("name", snapshot.get("ticker", "")),
        "ticker": snapshot["ticker"],
        "type": "benchmark",
        "currency": price.get("currency") or "",
        "price": {"last": price.get("current")},
        "performance": perf,
        "volatility_30d": snapshot.get("volatility_30d"),
        "quality_flags": [],
        "source_url": snapshot.get("source_url"),
    }


def _is_milan_ticker(ticker: str) -> bool:
    return ticker.upper().endswith(".MI")


def _search_name(company_name: str) -> str:
    """Short company name for news queries (drop legal suffixes)."""
    for suffix in (" S.p.A.", " SpA", " S.p.a.", " plc", " Inc.", " Corp.", " N.V."):
        if company_name.endswith(suffix):
            return company_name[: -len(suffix)].strip()
    return company_name


def _global_press_suffix() -> str:
    return "Reuters OR Bloomberg OR CNBC OR MarketWatch OR Financial Times"


def _is_bank_issuer(item: dict[str, Any]) -> bool:
    sector = (item.get("sector") or "").lower()
    industry = (item.get("industry") or "").lower()
    blob = f"{sector} {industry}"
    return any(token in blob for token in ("bank", "banc", "financial service"))


def _stock_issuer_event_query_sets(
    item: dict[str, Any], *, current_year: int
) -> tuple[list[str], list[str]]:
    """Official-source news queries built from issuer identity (name/ticker/sites)."""
    query_name = _search_name(item["name"])
    ticker = item["ticker"]

    local_queries: list[str] = []
    if _is_milan_ticker(ticker):
        local_queries = [
            f'"{query_name}" OR {ticker} site:borsaitaliana.it',
            f"{ticker} site:borsaitaliana.it",
            f'"{query_name}" OR {ticker} site:consob.it',
        ]
        if _is_bank_issuer(item):
            local_queries.append(f'"{query_name}" OR {ticker} site:bancaditalia.it')
    elif ticker.upper().endswith(".DE"):
        local_queries = [
            f'"{query_name}" OR {ticker} site:bafin.de',
            f'"{query_name}" OR {ticker} site:deutsche-boerse.com',
        ]

    global_queries = [
        f'"{query_name}" OR {ticker} news {current_year}',
    ]
    return local_queries, global_queries


def iter_stock_issuer_event_query_sets(
    item: dict[str, Any], *, current_year: int
) -> tuple[list[str], list[str]]:
    return _stock_issuer_event_query_sets(item, current_year=current_year)


def _nasdaq_news_query_sets(item: dict[str, Any], *, current_year: int) -> list[str]:
    """NASDAQ.com news queries from instrument identity (name, ticker, category)."""
    if item.get("type") == "etf":
        short_name = _etf_short_name(item["name"])
        ticker = item["ticker"]
        etf_data = item.get("etf") or {}
        category = str(etf_data.get("category") or item.get("profile") or "").strip()
        queries = [
            f'"{short_name}" site:nasdaq.com {current_year}',
            f"{ticker} site:nasdaq.com",
        ]
        if category and category.lower() not in short_name.lower():
            queries.append(f'"{category}" site:nasdaq.com {current_year}')
        return queries

    query_name = _search_name(item["name"])
    ticker = item["ticker"]
    return [
        f'"{query_name}" site:nasdaq.com {current_year}',
        f"{ticker} site:nasdaq.com",
    ]


def iter_nasdaq_news_query_sets(item: dict[str, Any], *, current_year: int) -> list[str]:
    return _nasdaq_news_query_sets(item, current_year=current_year)


def _format_nasdaq_query_block(queries: list[str]) -> list[str]:
    if not queries:
        return []
    lines = ["**NASDAQ / US** (Search NASDAQ news with Serper):"]
    for index, query in enumerate(queries, start=1):
        lines.append(f"{index}. {query}")
    return lines


def build_institutional_sources_guide(*, language: str = "English") -> str:
    """Guide for official issuer/regulatory sources the news analyst must check."""
    if language.lower().startswith("ital"):
        return (
            "Fonti istituzionali da consultare per titoli in watchlist (priorità HIGH):\n"
            "- **Borsa Italiana** (borsaitaliana.it): comunicati, avvisi, documenti societari\n"
            "- **CONSOB** (consob.it): provvedimenti, sanzioni, disclosure obbligatorie\n"
            "- **Banca d'Italia**: documenti di supervisione — ranking penalizza PDF/rapporti "
            "statici vs notizie recenti su Borsa Italiana\n"
            "- **BaFin / Deutsche Börse**: per titoli .DE\n"
            "- **NASDAQ** (nasdaq.com): notizie US utili soprattutto per ETF tematici\n"
            "Cerca notizie recenti sull'emittente su fonti ufficiali — priorità a Borsa Italiana."
        )
    return (
        "Institutional sources to check for watchlist issuers (high priority):\n"
        "- **Borsa Italiana** (borsaitaliana.it): company announcements and market notices\n"
        "- **CONSOB** (consob.it): sanctions, enforcement, mandatory disclosures\n"
        "- **Bank of Italy**: supervision documents — ranking penalises static PDFs vs "
        "recent Borsa Italiana news\n"
        "- **BaFin / Deutsche Börse**: for .DE listings\n"
        "- **NASDAQ** (nasdaq.com): US market news, especially relevant for thematic ETFs\n"
        "Look for official corporate events, market operations, fines/sanctions/investigations "
        "and serious regulatory issues — before generic sector commentary."
    )


def _stock_serper_query_sets(
    item: dict[str, Any], *, current_year: int
) -> tuple[list[str], list[str]]:
    """Return (local/Italy queries, global/world queries) for a stock."""
    name = item["name"]
    query_name = _search_name(name)
    ticker = item["ticker"]
    sector = item.get("sector") or item.get("industry") or ""

    global_queries = [
        f'"{query_name}" OR {ticker} stock news {current_year}',
        f'"{query_name}" OR {ticker} {_global_press_suffix()} {current_year}',
        f"{ticker} earnings OR results OR outlook {current_year}",
    ]
    if sector:
        global_queries.append(f'"{sector}" sector stocks news {current_year}')

    local_queries: list[str] = []
    if _is_milan_ticker(ticker):
        local_queries = [
            f'"{query_name}" notizie {current_year}',
            f'"{query_name}" ultime notizie',
            f'"{query_name}" OR {ticker} notizie Italia {current_year}',
            f"{ticker} borsa italiana notizie {current_year}",
            f'"{query_name}" site:ilsole24ore.com',
            f'"{query_name}" site:ansa.it OR site:milanofinanza.it',
            f"{ticker} site:borsaitaliana.it OR site:repubblica.it/economia",
            f'"{query_name}" utili risultati trimestre {current_year}',
            f'"{query_name}" banca Italia mercato {current_year}',
        ]
    return local_queries, global_queries


def _stock_serper_queries(item: dict[str, Any], *, current_year: int) -> list[str]:
    local, global_q = _stock_serper_query_sets(item, current_year=current_year)
    return local + global_q


def iter_stock_serper_queries(item: dict[str, Any], *, current_year: int) -> list[str]:
    """Public iterator for stock Serper queries (prefetch + agent checklist)."""
    return _stock_serper_queries(item, current_year=current_year)


def iter_stock_serper_query_sets(
    item: dict[str, Any], *, current_year: int
) -> tuple[list[str], list[str]]:
    return _stock_serper_query_sets(item, current_year=current_year)


def _format_dual_query_block(
    local_queries: list[str],
    global_queries: list[str],
) -> list[str]:
    lines: list[str] = []
    if local_queries:
        lines.append("**Italy / local** (Search Italian financial news with Serper):")
        for index, query in enumerate(local_queries, start=1):
            lines.append(f"{index}. {query}")
    if global_queries:
        lines.append("**World / global** (Search recent financial news with Serper):")
        offset = 0 if not local_queries else len(local_queries)
        for index, query in enumerate(global_queries, start=1):
            lines.append(f"{index + offset}. {query}")
    return lines


def build_stock_news_queries(
    instruments: list[dict[str, Any]],
    *,
    current_year: int,
) -> str:
    """Mandatory Serper queries for watchlist stocks (issuer-specific news)."""
    stocks = [item for item in instruments if item.get("type") == "stock"]
    if not stocks:
        return "No individual stocks in watchlist — skip stock-specific searches."

    blocks: list[str] = [
        "Run EVERY query below. Italy → Search Italian financial news with Serper.",
        "World → Search recent financial news with Serper.",
        "NASDAQ → Search NASDAQ news with Serper.",
        "",
    ]
    for item in stocks:
        name = item["name"]
        ticker = item["ticker"]
        issuer_local, issuer_global = _stock_issuer_event_query_sets(
            item, current_year=current_year
        )
        local, global_q = _stock_serper_query_sets(item, current_year=current_year)
        blocks.append(f"### {name} ({ticker})")
        if issuer_local or issuer_global:
            blocks.append(
                "**Issuer events / institutional sources** "
                "(Search Italian financial news + Search recent financial news — run FIRST):"
            )
            for index, query in enumerate(issuer_local + issuer_global, start=1):
                blocks.append(f"{index}. {query}")
            blocks.append("")
        blocks.extend(_format_dual_query_block(local, global_q))
        nasdaq_queries = _nasdaq_news_query_sets(item, current_year=current_year)
        blocks.extend(_format_nasdaq_query_block(nasdaq_queries))
        blocks.append("")
    return "\n".join(blocks).rstrip()


def _etf_short_name(name: str) -> str:
    """Compact ETF name for search queries."""
    for fragment in (
        " UCITS ETF USD (Acc)",
        " UCITS ETF EUR (Acc)",
        " UCITS ETF USD Acc",
        " UCITS ETF EUR Acc",
        " UCITS ETF",
        " ETF USD (Acc)",
        " ETF",
    ):
        name = name.replace(fragment, "")
    return name.strip()


def _etf_theme_search_queries(
    name: str, category: str, *, current_year: int
) -> tuple[list[str], list[str]]:
    """Theme queries split into local (Italian) and global (world) variants."""
    text = f"{name} {category}".lower()
    local: list[str] = []
    global_q: list[str] = []
    theme_map: list[tuple[str, list[str], list[str]]] = [
        (
            "semiconductor",
            [
                f'"semiconduttori" notizie {current_year}',
                f"semiconduttori Borsa Italiana notizie {current_year}",
            ],
            [
                f'"semiconductor" stocks news {current_year}',
                f"Nvidia OR Broadcom OR ASML semiconductor news {current_year}",
            ],
        ),
        (
            "artificial intelligence",
            [f'"intelligenza artificiale" ETF notizie {current_year}'],
            [
                f'"artificial intelligence" ETF OR stocks news {current_year}',
                f"Nvidia OR OpenAI AI market news {current_year}",
            ],
        ),
        (
            "quantum",
            [f'"computazione quantistica" notizie {current_year}'],
            [f'"quantum computing" stocks OR ETF news {current_year}'],
        ),
        (
            "china",
            [f'"Cina" mercati azionari notizie {current_year}'],
            [
                f'"China" stock market OR ETF news {current_year}',
                f"MSCI China A shares news {current_year}",
            ],
        ),
        (
            "quality factor",
            [f'"fattore qualità" azioni notizie {current_year}'],
            [f'"quality factor" stocks ETF news {current_year}'],
        ),
        (
            "msci world",
            [f'"MSCI World" mercati globali notizie {current_year}'],
            [f'"MSCI World" global equities news {current_year}'],
        ),
    ]
    for keyword, local_queries, global_queries in theme_map:
        if keyword in text:
            local.extend(local_queries)
            global_q.extend(global_queries)
    if not global_q and category:
        global_q.append(f'"{category}" ETF news {current_year}')
        local.append(f'"{category}" ETF notizie {current_year}')
    return local, global_q


def _etf_serper_query_sets(
    item: dict[str, Any], *, current_year: int
) -> tuple[list[str], list[str]]:
    """Return (local queries, global queries) for an ETF."""
    name = item["name"]
    short_name = _etf_short_name(name)
    ticker = item["ticker"]
    etf_data = item.get("etf") or {}
    category = str(etf_data.get("category") or item.get("profile") or "")

    global_queries = [
        f'"{short_name}" OR {ticker} ETF news {current_year}',
        f"{ticker} ETF {_global_press_suffix()} {current_year}",
        f'"{short_name}" UCITS ETF global news {current_year}',
    ]
    if category and category != name:
        global_queries.append(f'"{category}" ETF news {current_year}')

    theme_local, theme_global = _etf_theme_search_queries(
        name, category, current_year=current_year
    )
    local_queries: list[str] = list(theme_local)
    global_queries.extend(theme_global)

    if _is_milan_ticker(ticker):
        local_queries.extend(
            [
                f'"{short_name}" OR {ticker} ETF notizie {current_year}',
                f'"{short_name}" ultime notizie ETF',
                f"{ticker} site:ilsole24ore.com OR site:etf.it OR site:borsaitaliana.it",
                f'"{short_name}" site:milanofinanza.it OR site:ansa.it',
            ]
        )
    elif ticker.upper().endswith(".DE"):
        local_queries.extend(
            [
                f'"{short_name}" site:justetf.com OR site:finanzen.net {current_year}',
                f"{ticker} XETRA ETF news {current_year}",
            ]
        )
    else:
        local_queries.append(f'"{short_name}" OR {ticker} ETF notizie {current_year}')

    return local_queries, global_queries


def _etf_serper_queries(item: dict[str, Any], *, current_year: int) -> list[str]:
    local, global_q = _etf_serper_query_sets(item, current_year=current_year)
    return local + global_q


def iter_etf_serper_queries(item: dict[str, Any], *, current_year: int) -> list[str]:
    """Public iterator for ETF Serper queries (prefetch + agent checklist)."""
    return _etf_serper_queries(item, current_year=current_year)


def iter_etf_serper_query_sets(
    item: dict[str, Any], *, current_year: int
) -> tuple[list[str], list[str]]:
    return _etf_serper_query_sets(item, current_year=current_year)


def build_etf_news_queries(
    instruments: list[dict[str, Any]],
    *,
    current_year: int,
) -> str:
    """Mandatory Serper queries for watchlist ETFs (fund + theme news)."""
    etfs = [item for item in instruments if item.get("type") == "etf"]
    if not etfs:
        return "No ETFs in watchlist — skip ETF-specific searches."

    blocks: list[str] = [
        "Run EVERY query below. Italy → Search Italian financial news with Serper.",
        "World → Search recent financial news with Serper.",
        "NASDAQ → Search NASDAQ news with Serper.",
        "",
    ]
    for item in etfs:
        name = item["name"]
        ticker = item["ticker"]
        local, global_q = _etf_serper_query_sets(item, current_year=current_year)
        blocks.append(f"### {name} ({ticker})")
        blocks.extend(_format_dual_query_block(local, global_q))
        nasdaq_queries = _nasdaq_news_query_sets(item, current_year=current_year)
        blocks.extend(_format_nasdaq_query_block(nasdaq_queries))
        blocks.append("")
    return "\n".join(blocks).rstrip()


def build_instrument_profile_table(instruments: list[dict[str, Any]]) -> str:
    """Markdown table with ticker, type and inferred profile from market data."""
    lines = [
        "| Ticker | Type | Profile |",
        "|--------|------|---------|",
    ]
    for item in instruments:
        lines.append(
            f"| {item['ticker']} | {item['type']} | {item.get('profile', 'n/a')} |"
        )
    return "\n".join(lines)


def build_watchlist_performance_table(
    instruments: list[dict[str, Any]],
    *,
    language: str = "English",
    benchmarks: list[dict[str, Any]] | None = None,
) -> str:
    """Markdown performance snapshot with price, horizons, and one source ref per row."""
    italian = is_italian_language(language)
    if italian:
        header = (
            "| Ref | Strumento | Ticker | Prezzo (valuta) | Giornaliera | "
            "Settimanale | Mensile | YTD | 1A | Vol. 30g | Fonte |"
        )
        sep = (
            "|-----|-----------|--------|-----------------|-------------|"
            "-------------|---------|-----|-----|--------|-------|"
        )
    else:
        header = (
            "| Ref | Instrument | Ticker | Price (ccy) | 1D | 1W | 1M | YTD | 1Y | "
            "30d Vol | Source |"
        )
        sep = (
            "|-----|------------|--------|-------------|----|----|----|-----|-----|"
            "--------|--------|"
        )

    rows = list(instruments)
    if benchmarks:
        rows.extend(
            _benchmark_table_row(snapshot, italian=italian) for snapshot in benchmarks
        )

    lines = [header, sep]
    for item in rows:
        perf = item.get("performance", {})
        price = item.get("price", {})
        currency = item.get("currency") or ""
        citation = item.get("citation")
        ref = "—" if citation == "—" else f"[{citation}]"
        source_cell = ref
        if "1d_inconsistent" in item.get("quality_flags", []):
            source_cell = f"{ref} ⚠"
        vol = item.get("volatility_30d")
        vol_str = _fmt_pct(vol, italian=italian) if vol is not None else "n/a"
        lines.append(
            f"| {ref} | {item['name']} | {item['ticker']} "
            f"| {_fmt_price(price.get('last'), currency, italian=italian)} "
            f"| {_fmt_pct(perf.get('1d'), italian=italian)} "
            f"| {_fmt_pct(perf.get('1w'), italian=italian)} "
            f"| {_fmt_pct(perf.get('1m'), italian=italian)} "
            f"| {_fmt_pct(perf.get('ytd'), italian=italian)} "
            f"| {_fmt_pct(perf.get('1y'), italian=italian)} "
            f"| {vol_str} "
            f"| {source_cell} |"
        )
    return "\n".join(lines)


def build_market_pulse_table(
    instruments: list[dict[str, Any]],
    *,
    benchmarks: list[dict[str, Any]] | None = None,
) -> str:
    """Markdown table of watchlist performance for agent context."""
    lines = [
        "| Ref | Instrument | Ticker | Type | Last | 1D | 1W | 1M | YTD | 1Y | 30d Vol |",
        "|-----|------------|--------|------|------|----|----|----|-----|-----|---------|",
    ]
    rows = list(instruments)
    if benchmarks:
        rows.extend(
            _benchmark_table_row(snapshot, italian=False) for snapshot in benchmarks
        )
    for item in rows:
        perf = item.get("performance", {})
        price = item.get("price", {})
        currency = item.get("currency") or ""
        last = price.get("last")
        last_str = f"{_fmt_num(last)} {currency}" if last is not None else "n/a"
        citation = item.get("citation")
        ref = "—" if citation == "—" else f"[{citation}]"
        d1 = _fmt_pct(perf.get("1d"))
        if "1d_inconsistent" in item.get("quality_flags", []):
            d1 = f"{d1} ⚠"
        vol = item.get("volatility_30d")
        vol_str = _fmt_pct(vol) if vol is not None else "n/a"
        lines.append(
            f"| {ref} | {item['name']} | {item['ticker']} | {item['type']} "
            f"| {last_str} "
            f"| {d1} "
            f"| {_fmt_pct(perf.get('1w'))} "
            f"| {_fmt_pct(perf.get('1m'))} "
            f"| {_fmt_pct(perf.get('ytd'))} "
            f"| {_fmt_pct(perf.get('1y'))} "
            f"| {vol_str} |"
        )
    return "\n".join(lines)


def build_benchmark_context_block(benchmarks: list[dict[str, Any]]) -> str:
    """Compact benchmark summary for agent context (~2 lines per index)."""
    if not benchmarks:
        return ""
    lines = ["Benchmark rows (alpha vs beta reference — appended to performance tables):"]
    for snapshot in benchmarks:
        perf = snapshot.get("performance", {})
        lines.append(
            f"- {snapshot.get('name')} ({snapshot['ticker']}): "
            f"1D {_fmt_pct(perf.get('1d'))}, 1W {_fmt_pct(perf.get('1w'))}, "
            f"YTD {_fmt_pct(perf.get('ytd'))}"
        )
    return "\n".join(lines)


def build_watchlist_summary_checklist(instruments: list[dict[str, Any]]) -> str:
    """Explicit per-instrument checklist for mandatory Executive Summary coverage."""
    lines = [
        f"MANDATORY: Executive Summary / Sommario Esecutivo MUST mention ALL "
        f"{len(instruments)} instruments below — at least one sentence each with [N]:",
        "",
    ]
    for item in instruments:
        ref = f"[{item['citation']}]"
        perf = item.get("performance", {})
        d1 = _fmt_pct(perf.get("1d"))
        w1 = _fmt_pct(perf.get("1w"))
        ytd = _fmt_pct(perf.get("ytd"))
        lines.append(
            f"- {ref} **{instrument_label(item)}**: "
            f"cite 1D {d1}, 1W {w1}, YTD {ytd} and top news or driver {ref}"
        )
    return "\n".join(lines)


def build_briefing_section_headings(language: str) -> str:
    """Markdown checklist of ## headings for the chief strategist (one language only)."""
    lines = [
        "Use EXACTLY these ## section headings in this order — copy verbatim, no variants:",
        "",
    ]
    for index, key in enumerate(BRIEFING_SECTION_ORDER, start=2):
        lines.append(f"{index}. ## {localized_section_heading(key, language)}")
    lines.append("")
    if is_italian_language(language):
        lines.append("Write the briefing body in Italian. Do not use English section headings.")
    else:
        lines.append("Keep all section headings in English.")
    return "\n".join(lines)


def build_watchlist_driver_checklist(
    instruments: list[dict[str, Any]],
    *,
    language: str = "English",
) -> str:
    """Explicit per-instrument checklist for mandatory briefing coverage."""
    drivers_heading = (
        "Cosa Guida i Movimenti"
        if language.lower().startswith("ital")
        else "What's Driving the Moves"
    )
    lines = [
        f"MANDATORY: cover ALL {len(instruments)} instruments below — one entry each, "
        f"in this order, in '{drivers_heading}':",
        "",
    ]
    for item in instruments:
        ref = f"[{item['citation']}]"
        lines.append(
            f"- {ref} **{instrument_label(item)}**: "
            f"recent headline with a research citation (not Yahoo [1]-[N]); "
            f"if none found, explain 1D/1W move using market data {ref}"
        )
    return "\n".join(lines)


def build_watchlist_context(
    identities: list[InstrumentIdentity],
    snapshots: list[dict[str, Any]],
    *,
    session: str,
    language: str | None = None,
    benchmark_snapshots: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Build crew inputs from resolved identities and market snapshots."""
    briefing_language = language or get_default_language()
    now = datetime.now(MILAN_TZ)

    instruments = [
        _instrument_entry(identity, snapshot, citation=index + 1)
        for index, (identity, snapshot) in enumerate(zip(identities, snapshots))
    ]

    today = now.date()
    window_end = today + timedelta(days=28)

    forward_events = fetch_forward_calendar_events(
        instruments,
        window_start=today,
        window_end=window_end,
    )

    context = {
        "generated_at": now.isoformat(),
        "session": session,
        "session_label": SESSION_LABELS.get(session, session),
        "market": "Borsa Italiana (Milan)",
        "language": briefing_language,
        "current_date": now.date().isoformat(),
        "current_time": load_milan_sessions().get(session, "17:45"),
        "instrument_count": len(instruments),
        "instruments": [_slim_instrument_for_context(item) for item in instruments],
    }

    tickers = ", ".join(item["ticker"] for item in instruments)
    names = ", ".join(item["name"] for item in instruments)
    stock_names = ", ".join(
        item["name"] for item in instruments if item.get("type") == "stock"
    ) or "none"
    etf_names = ", ".join(
        item["name"] for item in instruments if item.get("type") == "etf"
    ) or "none"

    count = len(instruments)
    session_time = load_milan_sessions().get(session, "17:45")
    session_label = SESSION_LABELS.get(session, session)

    inputs = {
        "language": briefing_language,
        "session": session,
        "session_label": session_label,
        "current_date": today.isoformat(),
        "current_time": session_time,
        "calendar_window_start": today.isoformat(),
        "calendar_window_end": window_end.isoformat(),
        "market": "Borsa Italiana (Milan)",
        "instrument_count": str(count),
        "last_citation": str(count),
        "next_citation": str(count + 1),
        "watchlist_tickers": tickers,
        "watchlist_names": names,
        "watchlist_stocks": stock_names,
        "watchlist_etfs": etf_names,
        "watchlist_context": json.dumps(context, indent=2, ensure_ascii=False),
        "watchlist_instruments_json": json.dumps(
            instruments, ensure_ascii=False, indent=2
        ),
        "market_pulse_table": build_market_pulse_table(
            instruments, benchmarks=benchmark_snapshots
        ),
        "watchlist_performance_table": build_watchlist_performance_table(
            instruments,
            language=briefing_language,
            benchmarks=benchmark_snapshots,
        ),
        "benchmark_context": build_benchmark_context_block(benchmark_snapshots or []),
        "forward_calendar_table": build_forward_calendar_table(
            forward_events, language=briefing_language
        ),
        "recent_dated_events_table": "",
        "instrument_profile_table": build_instrument_profile_table(instruments),
        "watchlist_summary_checklist": build_watchlist_summary_checklist(instruments),
        "watchlist_driver_checklist": build_watchlist_driver_checklist(
            instruments, language=briefing_language
        ),
        "briefing_section_headings": build_briefing_section_headings(briefing_language),
        "instrument_naming_guide": build_instrument_naming_guide(instruments),
        "institutional_sources_guide": build_institutional_sources_guide(
            language=briefing_language
        ),
    }

    profile = resolve_session_profile(session_label, now)
    inputs.update(
        {
            "session_orientation": profile["session_orientation"],
            "valid_metrics": profile["valid_metrics"],
            "news_window": profile["news_window"],
            "calendar_split": profile["calendar_split"],
        }
    )
    return inputs


def attach_prefetched_news(context: dict[str, str]) -> dict[str, str]:
    """Add deterministic news digest and reference seed to crew inputs."""
    from financial_researcher.services.news_prefetch import prefetch_watchlist_news_bundle

    payload = json.loads(context["watchlist_context"])
    instruments = payload["instruments"]
    today = payload.get("current_date") or context.get("current_date", "")
    year = int(str(today)[:4]) if today else datetime.now(MILAN_TZ).year
    language = context.get("language", payload.get("language", "English"))
    start_citation = int(context.get("next_citation", payload.get("next_citation", 7)))
    print("▸ Prefetching news (Yahoo + Serper + Finnhub)...")
    context = dict(context)
    as_of = date.fromisoformat(str(today)) if today else None
    (
        digest,
        material,
        seed_markdown,
        seed_entries,
        headlines_by_ticker,
    ) = prefetch_watchlist_news_bundle(
        instruments,
        current_year=year,
        as_of_date=as_of,
        language=language,
        start_citation=start_citation,
    )
    context["prefetched_news_digest"] = digest
    context["watchlist_material_news"] = material
    context["research_reference_seed"] = seed_markdown
    context["research_reference_seed_json"] = json.dumps(
        seed_entries, ensure_ascii=False, indent=2
    )
    if as_of:
        context["recent_dated_events_table"] = build_recent_dated_events_table(
            instruments,
            headlines_by_ticker,
            as_of=as_of,
        )
    return context


def load_milan_sessions() -> dict[str, str]:
    """Load session name → HH:MM mapping from sessions_milan.yaml."""
    if not SESSIONS_PATH.exists():
        return {"pre_open": "08:45", "post_open": "09:30", "midday": "13:00", "close": "17:45"}
    with SESSIONS_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data.get("sessions", {})


def _easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday (Anonymous/Meeus computus)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def milan_market_holidays(year: int) -> set[date]:
    """Euronext Milan (Borsa Italiana) full-closure trading holidays for a year.

    Includes only days the exchange is fully closed: New Year's Day, Good Friday,
    Easter Monday, Labour Day, Christmas Day and St. Stephen's Day. Other Italian
    civic holidays (e.g. Ferragosto, Republic Day) do not close the exchange.
    """
    easter = _easter_sunday(year)
    return {
        date(year, 1, 1),            # New Year's Day
        easter - timedelta(days=2),  # Good Friday
        easter + timedelta(days=1),  # Easter Monday
        date(year, 5, 1),            # Labour Day
        date(year, 12, 25),          # Christmas Day
        date(year, 12, 26),          # St. Stephen's Day
    }


def is_milan_market_closed(moment: datetime | None = None) -> bool:
    """True when Borsa Italiana is closed for the day (weekend or holiday)."""
    moment = moment or datetime.now(MILAN_TZ)
    if moment.weekday() >= 5:  # Saturday (5) or Sunday (6)
        return True
    return moment.date() in milan_market_holidays(moment.year)


def infer_milan_session(when: datetime | None = None) -> str:
    """Return the Milan session whose scheduled time most recently passed today.

    When Borsa Italiana is closed (weekend or trading holiday) the only meaningful
    data is the last available close, so always return ``close`` regardless of the
    clock.
    """
    moment = when or datetime.now(MILAN_TZ)
    if is_milan_market_closed(moment):
        return "close"
    current = moment.strftime("%H:%M")
    sessions = load_milan_sessions()
    ordered = sorted(sessions.items(), key=lambda item: item[1])

    chosen = ordered[0][0]
    for name, scheduled in ordered:
        if scheduled <= current:
            chosen = name
    return chosen


def briefing_output_path(session: str, when: datetime | None = None) -> str:
    """Path for the unified watchlist briefing file."""
    from financial_researcher.paths import briefings_dir

    moment = when or datetime.now(MILAN_TZ)
    filename = f"watchlist_{moment.date().isoformat()}_{session}.md"
    return str(briefings_dir() / filename)
