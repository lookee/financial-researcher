"""Fetch and cache Yahoo Finance market snapshots for watchlist briefings."""

from datetime import date
from typing import Any

import pandas as pd
import yfinance as yf

from financial_researcher.models.instrument import InstrumentIdentity
from financial_researcher.storage.market_cache import MarketCache


class MarketDataService:
    """Build a structured market snapshot for briefing context."""

    def __init__(self, cache: MarketCache | None = None):
        self.cache = cache or MarketCache()

    def get_snapshot(
        self,
        identity: InstrumentIdentity,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        if use_cache:
            cached = self.cache.get(identity.isin)
            if cached:
                data = cached["data"]
                if data.get("ticker") == identity.primary_ticker:
                    return data

        snapshot = self._fetch_snapshot(identity)
        self.cache.save(identity.isin, snapshot)
        return snapshot

    def _fetch_snapshot(self, identity: InstrumentIdentity) -> dict[str, Any]:
        ticker = yf.Ticker(identity.primary_ticker)
        info = ticker.info or {}
        history = ticker.history(period="1y", auto_adjust=True)

        performance = self._calculate_performance(history)
        source_url = (
            f"https://finance.yahoo.com/quote/{identity.primary_ticker}"
        )

        return {
            "fetched_on": date.today().isoformat(),
            "source": "Yahoo Finance",
            "source_url": source_url,
            "ticker": identity.primary_ticker,
            "instrument_type": identity.instrument_type,
            "price": {
                "current": info.get("currentPrice") or info.get("regularMarketPrice"),
                "previous_close": info.get("previousClose"),
                "currency": info.get("currency") or identity.currency,
                "change_percent": info.get("regularMarketChangePercent"),
            },
            "performance": performance,
            "profile": {
                "sector": info.get("sector") or identity.sector,
                "industry": info.get("industry") or identity.industry,
                "market_cap": info.get("marketCap"),
            },
            "fundamentals": self._extract_fundamentals(info, identity.instrument_type),
            "forecasts": self._extract_forecasts(info, identity.instrument_type),
        }

    def _calculate_performance(self, history: pd.DataFrame) -> dict[str, float | None]:
        if history.empty or "Close" not in history.columns:
            return {
                "1d": None,
                "1w": None,
                "1m": None,
                "3m": None,
                "1y": None,
                "ytd": None,
            }

        closes = history["Close"].dropna()
        latest = float(closes.iloc[-1])

        def pct_change(days: int | None) -> float | None:
            if days is None:
                return None
            if len(closes) <= days:
                return None
            previous = float(closes.iloc[-(days + 1)])
            if previous == 0:
                return None
            return round(((latest - previous) / previous) * 100, 2)

        ytd_start = closes[closes.index.year == date.today().year]
        ytd = None
        if not ytd_start.empty:
            first = float(ytd_start.iloc[0])
            if first:
                ytd = round(((latest - first) / first) * 100, 2)

        return {
            "1d": pct_change(1),
            "1w": pct_change(5),
            "1m": pct_change(21),
            "3m": pct_change(63),
            "1y": pct_change(252) if len(closes) > 252 else pct_change(len(closes) - 1),
            "ytd": ytd,
        }

    def _extract_fundamentals(
        self, info: dict[str, Any], instrument_type: str
    ) -> dict[str, Any]:
        if instrument_type == "etf":
            return {
                "aum": info.get("totalAssets"),
                "category": info.get("category"),
                "fund_family": info.get("fundFamily"),
            }

        return {
            "pe_ratio": info.get("trailingPE") or info.get("forwardPE"),
        }

    def _extract_forecasts(
        self, info: dict[str, Any], instrument_type: str
    ) -> dict[str, Any] | None:
        if instrument_type == "etf":
            return None

        target_mean = info.get("targetMeanPrice")
        if not target_mean:
            return None

        return {
            "target_mean": target_mean,
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "recommendation": info.get("recommendationKey"),
            "analyst_count": info.get("numberOfAnalystOpinions"),
            "source": "Yahoo Finance Analyst Data",
        }
