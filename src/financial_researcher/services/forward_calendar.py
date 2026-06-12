"""Deterministic forward event calendar from Yahoo Finance."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import yfinance as yf

from financial_researcher.services.retry import with_retries

IMPACT_EARNINGS = "Earnings"
IMPACT_CORPORATE = "Corporate action"


def _parse_yahoo_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value).date()
        except (OSError, ValueError, OverflowError):
            return None
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    if isinstance(value, (list, tuple)) and value:
        return _parse_yahoo_date(value[0])
    return None


def _events_from_ticker_info(
    item: dict[str, Any],
    info: dict[str, Any],
    *,
    window_start: date,
    window_end: date,
) -> list[dict[str, Any]]:
    if item.get("type") != "stock":
        return []

    events: list[dict[str, Any]] = []
    ticker = item["ticker"]
    name = item["name"]
    source_url = f"https://finance.yahoo.com/quote/{ticker}"

    earnings = _parse_yahoo_date(info.get("earningsDate") or info.get("earningsTimestamp"))
    if earnings and window_start <= earnings <= window_end:
        events.append(
            {
                "date": earnings.isoformat(),
                "event": f"{name} earnings release",
                "tickers": ticker,
                "impact": IMPACT_EARNINGS,
                "source_url": source_url,
            }
        )

    for field, label, impact in (
        ("exDividendDate", "ex-dividend date", IMPACT_CORPORATE),
        ("dividendDate", "dividend payment", IMPACT_CORPORATE),
    ):
        event_date = _parse_yahoo_date(info.get(field))
        if event_date and window_start <= event_date <= window_end:
            events.append(
                {
                    "date": event_date.isoformat(),
                    "event": f"{name} {label}",
                    "tickers": ticker,
                    "impact": impact,
                    "source_url": source_url,
                }
            )
    return events


def fetch_forward_calendar_events(
    instruments: list[dict[str, Any]],
    *,
    window_start: date,
    window_end: date,
) -> list[dict[str, Any]]:
    """Collect confirmed forward stock events from yfinance within the window."""
    events: list[dict[str, Any]] = []
    for item in instruments:
        if item.get("type") != "stock":
            continue
        try:
            info = with_retries(lambda t=item["ticker"]: yf.Ticker(t).info or {})
        except Exception:
            continue
        events.extend(
            _events_from_ticker_info(
                item,
                info,
                window_start=window_start,
                window_end=window_end,
            )
        )
    events.sort(key=lambda row: row["date"])
    return events


def build_forward_calendar_table(
    events: list[dict[str, Any]],
    *,
    language: str = "English",
) -> str:
    """Markdown table of confirmed forward events for calendar_analyst context."""
    if not events:
        return "No confirmed forward events in window (Yahoo Finance calendar fields)."

    if language.lower().startswith("ital"):
        header = (
            "| Data (YYYY-MM-DD) | Evento | Strumenti | Impatto | Fonte |"
        )
        sep = "|---|---|---|---|---|"
    else:
        header = (
            "| Date (YYYY-MM-DD) | Event | Affected tickers/themes | Impact | Source |"
        )
        sep = "|---|---|---|---|---|"

    lines = [header, sep]
    for row in events:
        lines.append(
            f"| {row['date']} | {row['event']} | {row['tickers']} | "
            f"{row['impact']} | {row['source_url']} |"
        )
    return "\n".join(lines)


def build_recent_dated_events_table(
    instruments: list[dict[str, Any]],
    headlines_by_ticker: dict[str, list[dict[str, str]]],
    *,
    as_of: date,
    lookback_days: int = 14,
) -> str:
    """Past dated news items — not forward calendar."""
    cutoff = as_of - timedelta(days=lookback_days)
    rows: list[tuple[str, str, str, str]] = []
    for item in instruments:
        for headline in headlines_by_ticker.get(item["ticker"], []):
            published = headline.get("published_date") or headline.get("date", "")
            try:
                event_date = date.fromisoformat(published[:10])
            except ValueError:
                continue
            if event_date > as_of or event_date < cutoff:
                continue
            rows.append(
                (
                    event_date.isoformat(),
                    item["ticker"],
                    headline.get("title", "")[:80],
                    headline.get("url", ""),
                )
            )
    rows.sort(key=lambda row: row[0], reverse=True)
    if not rows:
        return "No recent dated news events in the last 14 days."
    lines = [
        "| Date (YYYY-MM-DD) | Ticker | Headline | Source |",
        "|---|---|---|---|",
    ]
    for event_date, ticker, title, url in rows[:20]:
        lines.append(f"| {event_date} | {ticker} | {title} | {url} |")
    return "\n".join(lines)
