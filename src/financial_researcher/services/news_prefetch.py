"""Deterministic news prefetch (Yahoo + Serper) for the news analyst."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

from financial_researcher.services.watchlist_context import (
    iter_etf_serper_query_sets,
    iter_stock_serper_query_sets,
)

MILAN_TZ = ZoneInfo("Europe/Rome")
SERPER_NEWS_URL = "https://google.serper.dev/news"


def _parse_yahoo_news_item(raw: dict[str, Any]) -> dict[str, str] | None:
    content = raw.get("content") or raw
    title = (content.get("title") or "").strip()
    if not title:
        return None
    pub = content.get("pubDate") or content.get("displayTime") or ""
    date_str = pub[:10] if pub else "n/a"
    url = content.get("previewUrl") or content.get("link") or ""
    provider = content.get("provider") or {}
    source = provider.get("displayName") or provider.get("name") or "Yahoo Finance"
    summary = (content.get("summary") or content.get("description") or "").strip()
    return {
        "date": date_str,
        "title": title,
        "source": source,
        "url": url,
        "summary": summary[:280],
        "region": "Yahoo",
    }


def fetch_yahoo_news(ticker: str, *, limit: int = 8) -> list[dict[str, str]]:
    """Fetch recent Yahoo Finance headlines for a ticker."""
    items: list[dict[str, str]] = []
    try:
        for raw in (yf.Ticker(ticker).news or [])[: limit * 2]:
            if not isinstance(raw, dict):
                continue
            parsed = _parse_yahoo_news_item(raw)
            if parsed:
                items.append(parsed)
            if len(items) >= limit:
                break
    except Exception:
        return items
    return items


def _serper_locale(ticker: str) -> tuple[str, str]:
    upper = ticker.upper()
    if upper.endswith(".MI"):
        return "it", "it"
    if upper.endswith(".DE"):
        return "de", "de"
    return "", ""


def _serper_news(
    query: str,
    *,
    country: str = "",
    locale: str = "",
    num: int = 8,
    region: str = "",
) -> list[dict[str, str]]:
    api_key = os.getenv("SERPER_API_KEY", "").strip()
    if not api_key:
        return []

    payload: dict[str, Any] = {"q": query, "num": num}
    if country:
        payload["gl"] = country
    if locale:
        payload["hl"] = locale

    try:
        response = requests.post(
            SERPER_NEWS_URL,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return []

    label = region or (f"Serper {country.upper()}" if country else "Serper global")
    headlines: list[dict[str, str]] = []
    for item in data.get("news") or []:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        headlines.append(
            {
                "date": (item.get("date") or "n/a").strip(),
                "title": title,
                "source": (item.get("source") or label).strip(),
                "url": (item.get("link") or "").strip(),
                "summary": (item.get("snippet") or "").strip()[:280],
                "query": query,
                "region": label,
            }
        )
    return headlines


def _fetch_serper_dual(
    item: dict[str, Any],
    *,
    current_year: int,
    max_local_queries: int,
    max_global_queries: int,
) -> list[dict[str, str]]:
    if item.get("type") == "stock":
        local_queries, global_queries = iter_stock_serper_query_sets(
            item, current_year=current_year
        )
    else:
        local_queries, global_queries = iter_etf_serper_query_sets(
            item, current_year=current_year
        )

    country, locale = _serper_locale(item["ticker"])
    items: list[dict[str, str]] = []

    for query in local_queries[:max_local_queries]:
        if country:
            items.extend(
                _serper_news(
                    query,
                    country=country,
                    locale=locale,
                    num=6,
                    region=f"Serper {country.upper()}",
                )
            )

    for query in global_queries[:max_global_queries]:
        items.extend(_serper_news(query, num=6, region="Serper global"))

    return items


def _dedupe_headlines(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in items:
        key = item.get("url") or item.get("title", "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _format_headline_line(item: dict[str, str]) -> str:
    date = item.get("date") or "n/a"
    title = item.get("title") or "Untitled"
    source = item.get("source") or "Unknown"
    region = item.get("region") or ""
    url = item.get("url") or ""
    summary = item.get("summary") or ""
    region_tag = f" [{region}]" if region else ""
    line = f"- {date} | **{title}** | {source}{region_tag}"
    if url:
        line += f" | {url}"
    if summary:
        line += f"\n  {summary}"
    return line


def prefetch_watchlist_news(
    instruments: list[dict[str, Any]],
    *,
    current_year: int | None = None,
    max_local_queries: int = 5,
    max_global_queries: int = 5,
    max_headlines_per_ticker: int = 16,
) -> str:
    """Build a markdown digest of pre-fetched Yahoo + Serper news per ticker."""
    year = current_year or datetime.now(MILAN_TZ).year
    has_serper = bool(os.getenv("SERPER_API_KEY", "").strip())

    lines = [
        "Pre-fetched headlines (deterministic). The news analyst MUST review ALL entries",
        "below before writing. Coverage includes Yahoo + Serper Italy/local + Serper global.",
        "Include every material headline in the output brief.",
        "",
    ]

    for item in instruments:
        ticker = item["ticker"]
        name = item["name"]
        lines.append(f"### {name} ({ticker})")

        yahoo_items = fetch_yahoo_news(ticker)
        serper_items: list[dict[str, str]] = []
        if has_serper:
            serper_items = _fetch_serper_dual(
                item,
                current_year=year,
                max_local_queries=max_local_queries,
                max_global_queries=max_global_queries,
            )
        else:
            lines.append("- _Serper prefetch skipped (SERPER_API_KEY not set)._")

        combined = _dedupe_headlines(yahoo_items + serper_items)[:max_headlines_per_ticker]

        if not combined:
            lines.append("- _No headlines returned from Yahoo or Serper prefetch._")
        else:
            lines.extend(_format_headline_line(headline) for headline in combined)

        lines.append("")

    return "\n".join(lines).rstrip()
