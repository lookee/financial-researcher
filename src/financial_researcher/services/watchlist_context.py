"""Build aggregated watchlist context for the briefing crew."""

import json
from datetime import datetime
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


def _metadata_for_isin(
    isin: str, watchlist_items: list[dict[str, Any]] | None
) -> dict[str, Any]:
    if not watchlist_items:
        return {}
    for item in watchlist_items:
        if item.get("isin", "").upper() == isin.upper():
            return {
                key: item[key]
                for key in ("theme", "drivers")
                if item.get(key)
            }
    return {}


def _instrument_entry(
    identity: InstrumentIdentity,
    snapshot: dict[str, Any],
    citation: int,
    metadata: dict[str, Any] | None = None,
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

    if metadata:
        entry.update(metadata)

    return entry


def build_theme_map_table(instruments: list[dict[str, Any]]) -> str:
    """Markdown table mapping each instrument to its thematic drivers."""
    lines = [
        "| Ticker | Theme | Key Drivers |",
        "|--------|-------|-------------|",
    ]
    for item in instruments:
        theme = item.get("theme") or "n/a"
        drivers = item.get("drivers") or []
        driver_text = "; ".join(drivers) if drivers else "n/a"
        lines.append(f"| {item['ticker']} | {theme} | {driver_text} |")
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
    watchlist_items: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """Build crew inputs from resolved identities and market snapshots."""
    briefing_language = language or get_default_language()
    now = datetime.now(MILAN_TZ)

    instruments = [
        _instrument_entry(
            identity,
            snapshot,
            citation=index + 1,
            metadata=_metadata_for_isin(identity.isin, watchlist_items),
        )
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

    count = len(instruments)

    return {
        "language": briefing_language,
        "session": session,
        "session_label": SESSION_LABELS.get(session, session),
        "current_date": now.date().isoformat(),
        "current_time": now.strftime("%H:%M"),
        "market": "Borsa Italiana (Milan)",
        "instrument_count": str(count),
        "last_citation": str(count),
        "next_citation": str(count + 1),
        "watchlist_tickers": tickers,
        "watchlist_names": names,
        "watchlist_context": json.dumps(context, indent=2, ensure_ascii=False),
        "market_pulse_table": build_market_pulse_table(instruments),
        "theme_map_table": build_theme_map_table(instruments),
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
