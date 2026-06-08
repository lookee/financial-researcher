"""Build aggregated watchlist context for the briefing crew."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from financial_researcher.models.instrument import InstrumentIdentity
from financial_researcher.settings import get_default_language

MILAN_TZ = ZoneInfo("Europe/Rome")
SESSIONS_PATH = Path(__file__).parent.parent / "config" / "sessions_milan.yaml"

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


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{_fmt_num(value)}%"


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

    return entry


def _is_milan_ticker(ticker: str) -> bool:
    return ticker.upper().endswith(".MI")


def _search_name(company_name: str) -> str:
    """Short company name for news queries (drop legal suffixes)."""
    for suffix in (" S.p.A.", " SpA", " S.p.a.", " plc", " Inc.", " Corp.", " N.V."):
        if company_name.endswith(suffix):
            return company_name[: -len(suffix)].strip()
    return company_name


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
        "Run EVERY query below with SerperNewsTool (news search) before writing.",
        "Use Italian for .MI tickers. Do not narrow to OPS/OPA/capital operations only.",
        "",
    ]
    for item in stocks:
        name = item["name"]
        query_name = _search_name(name)
        ticker = item["ticker"]
        sector = item.get("sector") or item.get("industry") or ""
        blocks.append(f"### {name} ({ticker})")
        blocks.append(f'1. "{query_name}" notizie {current_year}')
        blocks.append(f'2. "{query_name}" OR {ticker} news {current_year}')
        if sector:
            blocks.append(f'3. "{query_name}" {sector} notizie {current_year}')
        if _is_milan_ticker(ticker):
            blocks.append(
                f'4. "{query_name}" site:ilsole24ore.com OR site:ansa.it OR site:milanofinanza.it'
            )
            blocks.append(
                f'5. {ticker} site:borsaitaliana.it OR site:repubblica.it/economia'
            )
        else:
            blocks.append(f'4. {ticker} financial news {current_year}')
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


def _etf_theme_query(name: str, category: str, *, current_year: int) -> str | None:
    """Optional thematic query inferred from ETF name or category."""
    text = f"{name} {category}".lower()
    themes: list[tuple[str, str]] = [
        ("semiconductor", f'"semiconductor" OR "semiconduttori" ETF notizie {current_year}'),
        ("artificial intelligence", f'"artificial intelligence" OR "intelligenza artificiale" ETF notizie {current_year}'),
        ("quantum", f'"quantum computing" OR "computazione quantistica" ETF notizie {current_year}'),
        ("china", f'"China" OR "Cina" ETF notizie mercati {current_year}'),
        ("quality factor", f'"quality factor" OR fattore qualità ETF notizie {current_year}'),
        ("msci world", f'"MSCI World" ETF notizie {current_year}'),
    ]
    for keyword, query in themes:
        if keyword in text:
            return query
    if category:
        return f'"{category}" ETF notizie {current_year}'
    return None


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
        "Run EVERY query below with SerperNewsTool (news search) before writing.",
        "Use Italian for .MI ETFs where relevant.",
        "",
    ]
    for item in etfs:
        name = item["name"]
        short_name = _etf_short_name(name)
        ticker = item["ticker"]
        etf_data = item.get("etf") or {}
        category = etf_data.get("category") or item.get("profile") or ""
        blocks.append(f"### {name} ({ticker})")
        blocks.append(f'1. "{short_name}" OR {ticker} ETF notizie {current_year}')
        blocks.append(f'2. {ticker} ETF news {current_year}')
        if category and category != name:
            blocks.append(f'3. "{category}" ETF notizie {current_year}')
        theme_query = _etf_theme_query(name, str(category), current_year=current_year)
        if theme_query:
            blocks.append(f"4. {theme_query}")
        if _is_milan_ticker(ticker):
            blocks.append(
                f'5. {ticker} site:ilsole24ore.com OR site:etf.it OR site:borsaitaliana.it'
            )
        elif ticker.upper().endswith(".DE"):
            blocks.append(
                f'5. "{short_name}" site:justetf.com OR site:finanzen.net {current_year}'
            )
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


def build_market_pulse_table(instruments: list[dict[str, Any]]) -> str:
    """Markdown table of watchlist performance for agent context."""
    lines = [
        "| Ref | Instrument | Ticker | Type | Last | 1D | 1W | 1M | YTD |",
        "|-----|------------|--------|------|------|----|----|----|-----|",
    ]
    for item in instruments:
        perf = item.get("performance", {})
        price = item.get("price", {})
        currency = item.get("currency") or ""
        last = price.get("last")
        last_str = f"{_fmt_num(last)} {currency}" if last is not None else "n/a"
        ref = f"[{item['citation']}]"
        lines.append(
            f"| {ref} | {item['name']} | {item['ticker']} | {item['type']} "
            f"| {last_str} {ref} "
            f"| {_fmt_pct(perf.get('1d'))} {ref} "
            f"| {_fmt_pct(perf.get('1w'))} {ref} "
            f"| {_fmt_pct(perf.get('1m'))} {ref} "
            f"| {_fmt_pct(perf.get('ytd'))} {ref} |"
        )
    return "\n".join(lines)


def build_watchlist_context(
    identities: list[InstrumentIdentity],
    snapshots: list[dict[str, Any]],
    *,
    session: str,
    language: str | None = None,
) -> dict[str, str]:
    """Build crew inputs from resolved identities and market snapshots."""
    briefing_language = language or get_default_language()
    now = datetime.now(MILAN_TZ)

    instruments = [
        _instrument_entry(identity, snapshot, citation=index + 1)
        for index, (identity, snapshot) in enumerate(zip(identities, snapshots))
    ]

    context = {
        "generated_at": now.isoformat(),
        "session": session,
        "session_label": SESSION_LABELS.get(session, session),
        "market": "Borsa Italiana (Milan)",
        "timezone": "Europe/Rome",
        "language": briefing_language,
        "current_date": now.date().isoformat(),
        "current_time": now.strftime("%H:%M"),
        "instrument_count": len(instruments),
        "instruments": instruments,
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
    today = now.date()
    window_end = today + timedelta(days=28)

    return {
        "language": briefing_language,
        "session": session,
        "session_label": SESSION_LABELS.get(session, session),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%H:%M"),
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
        "market_pulse_table": build_market_pulse_table(instruments),
        "instrument_profile_table": build_instrument_profile_table(instruments),
        "stock_news_queries": build_stock_news_queries(
            instruments, current_year=today.year
        ),
        "etf_news_queries": build_etf_news_queries(
            instruments, current_year=today.year
        ),
    }


def load_milan_sessions() -> dict[str, str]:
    """Load session name → HH:MM mapping from sessions_milan.yaml."""
    if not SESSIONS_PATH.exists():
        return {"pre_open": "08:45", "post_open": "09:30", "midday": "13:00", "close": "17:45"}
    with SESSIONS_PATH.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data.get("sessions", {})


def infer_milan_session(when: datetime | None = None) -> str:
    """Return the Milan session whose scheduled time most recently passed today."""
    moment = when or datetime.now(MILAN_TZ)
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
    moment = when or datetime.now(MILAN_TZ)
    return (
        f"output/briefings/watchlist_{moment.date().isoformat()}_{session}.md"
    )
