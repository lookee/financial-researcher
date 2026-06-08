"""Build aggregated watchlist context for the briefing crew."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from financial_researcher.models.instrument import InstrumentIdentity
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

    return entry


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
        lines.append("**Italia / locale** (Search Italian financial news with Serper):")
        for index, query in enumerate(local_queries, start=1):
            lines.append(f"{index}. {query}")
    if global_queries:
        lines.append("**Mondo / global** (Search recent financial news with Serper):")
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
        "Run EVERY query below before writing. Use BOTH Italy/local AND global/world coverage.",
        "Italia → Search Italian financial news with Serper (gl=it).",
        "Mondo → Search recent financial news with Serper (international sources).",
        "",
    ]
    for item in stocks:
        name = item["name"]
        ticker = item["ticker"]
        local, global_q = _stock_serper_query_sets(item, current_year=current_year)
        blocks.append(f"### {name} ({ticker})")
        blocks.extend(_format_dual_query_block(local, global_q))
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
        "Run EVERY query below before writing. Use BOTH Italy/local AND global/world coverage.",
        "Italia → Search Italian financial news with Serper. Mondo → Search recent financial news with Serper.",
        "ETF moves often follow global sector/theme news — always run global queries.",
        "",
    ]
    for item in etfs:
        name = item["name"]
        ticker = item["ticker"]
        local, global_q = _etf_serper_query_sets(item, current_year=current_year)
        blocks.append(f"### {name} ({ticker})")
        blocks.extend(_format_dual_query_block(local, global_q))
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
) -> str:
    """Markdown performance snapshot: daily, weekly, monthly, YTD (annual)."""
    italian = language.lower().startswith("ital")
    if italian:
        header = (
            "| Ref | Strumento | Ticker | Giornaliera | Settimanale | Mensile | Annuale (YTD) |"
        )
        sep = "|-----|-----------|--------|-------------|-------------|---------|---------------|"
    else:
        header = "| Ref | Instrument | Ticker | 1D | 1W | 1M | YTD |"
        sep = "|-----|------------|--------|----|----|----|-----|"

    lines = [header, sep]
    for item in instruments:
        perf = item.get("performance", {})
        ref = f"[{item['citation']}]"
        lines.append(
            f"| {ref} | {item['name']} | {item['ticker']} "
            f"| {_fmt_pct(perf.get('1d'))} {ref} "
            f"| {_fmt_pct(perf.get('1w'))} {ref} "
            f"| {_fmt_pct(perf.get('1m'))} {ref} "
            f"| {_fmt_pct(perf.get('ytd'))} {ref} |"
        )
    return "\n".join(lines)


def build_market_pulse_table(instruments: list[dict[str, Any]]) -> str:
    """Markdown table of watchlist performance for agent context."""
    lines = [
        "| Ref | Instrument | Ticker | Type | Last | 1D | 1W | 1M | 1Y | YTD |",
        "|-----|------------|--------|------|------|----|----|----|----|-----|",
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
            f"| {_fmt_pct(perf.get('1y'))} {ref} "
            f"| {_fmt_pct(perf.get('ytd'))} {ref} |"
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
    """Markdown checklist of ## headings for the chief strategist."""
    lines = [
        "Use EXACTLY these ## section headings in this order (English canonical titles):",
        "",
    ]
    for index, key in enumerate(BRIEFING_SECTION_ORDER, start=2):
        lines.append(f"{index}. ## {BRIEFING_SECTION_HEADINGS_EN[key]}")
    if language.lower().startswith("ital"):
        lines.extend(
            [
                "",
                "Write the briefing body in Italian. Translate each section heading into "
                "natural Italian (e.g. Sommario Esecutivo, Cosa Guida i Movimenti). "
                "Do not mix English and Italian headings in the same briefing.",
            ]
        )
    else:
        lines.append("")
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
        "current_time": load_milan_sessions().get(session, "17:45"),
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
    session_time = load_milan_sessions().get(session, "17:45")

    return {
        "language": briefing_language,
        "session": session,
        "session_label": SESSION_LABELS.get(session, session),
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
        "market_pulse_table": build_market_pulse_table(instruments),
        "watchlist_performance_table": build_watchlist_performance_table(
            instruments, language=briefing_language
        ),
        "instrument_profile_table": build_instrument_profile_table(instruments),
        "watchlist_summary_checklist": build_watchlist_summary_checklist(instruments),
        "watchlist_driver_checklist": build_watchlist_driver_checklist(
            instruments, language=briefing_language
        ),
        "briefing_section_headings": build_briefing_section_headings(briefing_language),
        "instrument_naming_guide": build_instrument_naming_guide(instruments),
        "stock_news_queries": build_stock_news_queries(
            instruments, current_year=today.year
        ),
        "etf_news_queries": build_etf_news_queries(
            instruments, current_year=today.year
        ),
    }


def attach_prefetched_news(context: dict[str, str]) -> dict[str, str]:
    """Add deterministic news digest to crew inputs."""
    from financial_researcher.services.news_prefetch import prefetch_watchlist_news

    payload = json.loads(context["watchlist_context"])
    instruments = payload["instruments"]
    today = payload.get("current_date") or context.get("current_date", "")
    year = int(str(today)[:4]) if today else datetime.now(MILAN_TZ).year
    print("Prefetching Yahoo + Serper news...")
    context = dict(context)
    context["prefetched_news_digest"] = prefetch_watchlist_news(
        instruments, current_year=year
    )
    return context


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
