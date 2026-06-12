"""Finnhub company-news provider for watchlist prefetch."""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from typing import Any

import requests

from financial_researcher.services.news_providers.base import NormalizedHeadline

FINNHUB_COMPANY_NEWS_URL = "https://finnhub.io/api/v1/company-news"
DEFAULT_LOOKBACK_DAYS = 14

# Best-effort map from Milan (or local) ticker bases to Finnhub company-news symbols.
# Finnhub indexes US/global listings; .MI codes often differ (e.g. STMMI → STM, GEM 1NVDA → NVDA).
# Extend this dict when prefetch misses news for a Milan stock — keys are uppercase bases without .MI.
MILAN_FINNHUB_SYMBOLS: dict[str, str] = {
    "STMMI": "STM",
    "ENI": "E",
    "RACE": "RACE",
    "ISP": "ISNPY",
}

_GEM_TICKER_RE = re.compile(r"^1([A-Z]{2,6})\.MI$", re.IGNORECASE)


def finnhub_enabled() -> bool:
    key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not key:
        return False
    flag = os.getenv("FINNHUB_ENABLED", "true").strip().lower()
    return flag not in {"0", "false", "no", "off"}


def finnhub_lookback_days() -> int:
    raw = os.getenv("FINNHUB_NEWS_LOOKBACK_DAYS", str(DEFAULT_LOOKBACK_DAYS)).strip()
    try:
        days = int(raw)
    except ValueError:
        return DEFAULT_LOOKBACK_DAYS
    return max(1, min(days, 30))


def resolve_finnhub_symbol(item: dict[str, Any]) -> str | None:
    """Map a watchlist instrument to a Finnhub company-news symbol."""
    if item.get("type") == "etf":
        return None

    ticker = (item.get("ticker") or "").upper().strip()
    if not ticker:
        return None

    gem_match = _GEM_TICKER_RE.match(ticker)
    if gem_match:
        return gem_match.group(1).upper()

    if ticker.endswith(".MI"):
        base = ticker[:-3]
        if base in MILAN_FINNHUB_SYMBOLS:
            return MILAN_FINNHUB_SYMBOLS[base]
        if base.isalpha() and 2 <= len(base) <= 5:
            return base

    if ticker.endswith(".DE") and ticker[:-3].isalpha():
        return ticker[:-3]

    if ticker in MILAN_FINNHUB_SYMBOLS:
        return MILAN_FINNHUB_SYMBOLS[ticker]

    if "." not in ticker and ticker.isalpha() and 1 <= len(ticker) <= 6:
        return ticker

    return None


class FinnhubNewsProvider:
    """Fetch company news from Finnhub for a single watchlist instrument."""

    def __init__(self, api_key: str | None = None, *, timeout: float = 12.0):
        self.api_key = (api_key or os.getenv("FINNHUB_API_KEY", "")).strip()
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key) and finnhub_enabled()

    def fetch(
        self,
        item: dict[str, Any],
        *,
        end_date: date | None = None,
        lookback_days: int | None = None,
    ) -> list[NormalizedHeadline]:
        if not self.available:
            return []

        symbol = resolve_finnhub_symbol(item)
        if not symbol:
            return []

        end = end_date or date.today()
        days = lookback_days if lookback_days is not None else finnhub_lookback_days()
        start = end - timedelta(days=days)

        try:
            response = requests.get(
                FINNHUB_COMPANY_NEWS_URL,
                params={
                    "symbol": symbol,
                    "from": start.isoformat(),
                    "to": end.isoformat(),
                    "token": self.api_key,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return []

        if not isinstance(payload, list):
            return []

        headlines: list[NormalizedHeadline] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            title = (row.get("headline") or row.get("title") or "").strip()
            if not title:
                continue
            raw_ts = row.get("datetime")
            date_str = "n/a"
            if isinstance(raw_ts, (int, float)) and raw_ts > 0:
                from datetime import datetime, timezone

                date_str = datetime.fromtimestamp(raw_ts, tz=timezone.utc).date().isoformat()
            url = (row.get("url") or "").strip()
            source = (row.get("source") or "Finnhub").strip()
            summary = (row.get("summary") or "").strip()[:120]
            headlines.append(
                NormalizedHeadline(
                    date=date_str,
                    title=title,
                    source=source,
                    url=url,
                    summary=summary,
                    region="Finnhub",
                    provider="finnhub",
                )
            )

        return headlines
