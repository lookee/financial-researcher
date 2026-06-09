"""Deterministic news prefetch (Yahoo + Serper) for the news analyst."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

from financial_researcher.services.news_ranking import (
    MATERIALITY_THRESHOLD,
    headline_relevance_score,
    impact_level,
    is_exchange_news,
    is_official_source,
)
from financial_researcher.services.watchlist_context import (
    instrument_label,
    iter_etf_serper_query_sets,
    iter_nasdaq_news_query_sets,
    iter_stock_issuer_event_query_sets,
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
        "summary": summary[:120],
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
    issuer_event: bool = False,
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
                "summary": (item.get("snippet") or "").strip()[:120],
                "query": query,
                "region": label,
                "issuer_event": "1" if issuer_event else "",
            }
        )
    return headlines


def _fetch_issuer_event_serper(
    item: dict[str, Any],
    *,
    current_year: int,
) -> list[dict[str, str]]:
    """Always run issuer/regulatory queries for stocks (not subject to query caps)."""
    if item.get("type") != "stock":
        return []

    local_queries, global_queries = iter_stock_issuer_event_query_sets(
        item, current_year=current_year
    )
    country, locale = _serper_locale(item["ticker"])
    items: list[dict[str, str]] = []

    for query in local_queries:
        items.extend(
            _serper_news(
                query,
                country=country,
                locale=locale,
                num=8,
                region="Serper IT issuer" if country == "it" else "Serper local issuer",
                issuer_event=True,
            )
        )

    for query in global_queries:
        items.extend(
            _serper_news(
                query,
                num=8,
                region="Serper global issuer",
                issuer_event=True,
            )
        )

    return items


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


def _fetch_nasdaq_serper(
    item: dict[str, Any],
    *,
    current_year: int,
    max_queries: int = 3,
) -> list[dict[str, str]]:
    """NASDAQ.com news via Serper (US market coverage, especially for thematic ETFs)."""
    queries = iter_nasdaq_news_query_sets(item, current_year=current_year)
    items: list[dict[str, str]] = []
    for query in queries[:max_queries]:
        items.extend(
            _serper_news(
                query,
                country="us",
                locale="en",
                num=6,
                region="Serper NASDAQ",
            )
        )
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


def _prioritize_headlines(
    items: list[dict[str, str]],
    *,
    instrument: dict[str, Any],
) -> list[dict[str, str]]:
    deduped = _dedupe_headlines(items)
    return sorted(
        deduped,
        key=lambda headline: (
            -headline_relevance_score(instrument, headline),
            headline.get("date", ""),
        ),
    )


def collect_instrument_headlines(
    item: dict[str, Any],
    *,
    current_year: int,
    max_local_queries: int = 5,
    max_global_queries: int = 5,
    max_nasdaq_queries: int = 3,
    max_headlines: int = 18,
) -> list[dict[str, str]]:
    """Fetch and rank headlines for one watchlist instrument."""
    ticker = item["ticker"]
    yahoo_items = fetch_yahoo_news(ticker)
    serper_items: list[dict[str, str]] = []

    if os.getenv("SERPER_API_KEY", "").strip():
        serper_items.extend(_fetch_issuer_event_serper(item, current_year=current_year))
        serper_items.extend(
            _fetch_serper_dual(
                item,
                current_year=current_year,
                max_local_queries=max_local_queries,
                max_global_queries=max_global_queries,
            )
        )
        serper_items.extend(
            _fetch_nasdaq_serper(
                item,
                current_year=current_year,
                max_queries=max_nasdaq_queries,
            )
        )

    return _prioritize_headlines(yahoo_items + serper_items, instrument=item)[:max_headlines]


def _format_headline_line(instrument: dict[str, Any], headline: dict[str, str]) -> str:
    date = headline.get("date") or "n/a"
    title = headline.get("title") or "Untitled"
    source = headline.get("source") or "Unknown"
    region = headline.get("region") or ""
    url = headline.get("url") or ""
    summary = headline.get("summary") or ""
    region_tag = f" [{region}]" if region else ""
    score = headline_relevance_score(instrument, headline)
    priority_tag = ""
    if score >= MATERIALITY_THRESHOLD:
        if is_exchange_news(headline):
            priority_tag = "**OFFICIAL SOURCE** | "
        elif is_official_source(headline):
            priority_tag = "**INSTITUTIONAL SOURCE** | "
        else:
            priority_tag = "**MATERIAL NEWS** | "
    line = f"- {priority_tag}{date} | **{title}** | {source}{region_tag}"
    if url:
        line += f" | {url}"
    if summary:
        line += f"\n  {summary}"
    return line


def build_research_reference_seed(
    instruments: list[dict[str, Any]],
    headlines_by_ticker: dict[str, list[dict[str, str]]],
    *,
    start_citation: int,
    headlines_per_instrument: int = 2,
) -> tuple[str, list[dict[str, Any]]]:
    """Assign fixed [{start_citation}+] numbers to top prefetch headlines per instrument."""
    entries: list[dict[str, Any]] = []
    citation = start_citation

    for item in instruments:
        headlines = [
            headline
            for headline in headlines_by_ticker.get(item["ticker"], [])
            if headline.get("url")
        ][:headlines_per_instrument]
        for headline in headlines:
            entries.append(
                {
                    "citation": citation,
                    "ticker": item["ticker"],
                    "name": item["name"],
                    "title": headline["title"],
                    "source": headline.get("source") or "Unknown",
                    "date": headline.get("date") or "n/a",
                    "url": headline["url"],
                    "score": headline_relevance_score(item, headline),
                }
            )
            citation += 1

    lines = [
        (
            f"Deterministic research citations [{start_citation}]+ for prefetch headlines. "
            "Use EXACTLY these numbers in news research and the final briefing References:"
        ),
        "",
    ]
    for entry in entries:
        lines.append(
            f"[{entry['citation']}] {entry['source']} — {entry['title']} — "
            f"{entry['date']} — {entry['url']}"
        )
    return "\n".join(lines), entries


def _seed_citation_for_headline(
    ticker: str,
    headline: dict[str, str],
    *,
    seed_entries: list[dict[str, Any]] | None = None,
) -> int | None:
    if not seed_entries:
        return None
    url = headline.get("url") or ""
    title = headline.get("title") or ""
    for entry in seed_entries:
        if url and entry.get("url") == url:
            return int(entry["citation"])
        if title and entry.get("title") == title and entry.get("ticker") == ticker:
            return int(entry["citation"])
    return None


def build_material_news_brief(
    instruments: list[dict[str, Any]],
    headlines_by_ticker: dict[str, list[dict[str, str]]],
    *,
    language: str = "English",
    seed_entries: list[dict[str, Any]] | None = None,
) -> str:
    """Ranked material headlines for chief strategist and news analyst."""
    italian = language.lower().startswith("ital")
    lines: list[str] = [
        "Material news ranking (structural scoring: recency, issuer match, source tier).",
        "Honour impact levels in the final memo.",
        "",
    ]

    high_impact: list[tuple[int, dict[str, Any], dict[str, str]]] = []

    for item in instruments:
        headlines = headlines_by_ticker.get(item["ticker"], [])
        ranked = sorted(
            headlines,
            key=lambda headline: -headline_relevance_score(item, headline),
        )
        material = [
            headline
            for headline in ranked
            if headline_relevance_score(item, headline) >= MATERIALITY_THRESHOLD
        ]
        label = instrument_label(item)

        if not material:
            lines.append(f"### {label}")
            if italian:
                lines.append("- Nessuna notizia rilevante in prefetch.")
            else:
                lines.append("- No relevant headline in prefetch.")
            lines.append("")
            continue

        top = material[0]
        score = headline_relevance_score(item, top)
        level = impact_level(item, top)
        lines.append(f"### {label} — Impact **{level}**")

        if italian:
            lines.append(f"- **Titolo da riportare**: {top['title']}")
            lines.append(f"- Data: {top.get('date', 'n/a')} | Fonte: {top.get('source', '')}")
        else:
            lines.append(f"- **Headline to report**: {top['title']}")
            lines.append(f"- Date: {top.get('date', 'n/a')} | Source: {top.get('source', '')}")

        if top.get("url"):
            lines.append(f"- URL: {top['url']}")
        if top.get("summary"):
            context_label = "Contesto" if italian else "Context"
            lines.append(f"- {context_label}: {top['summary']}")

        seed_citation = _seed_citation_for_headline(
            item["ticker"], top, seed_entries=seed_entries
        )
        if seed_citation is not None:
            cite_label = "Citazione obbligatoria" if italian else "Mandatory citation"
            lines.append(f"- **{cite_label}**: [{seed_citation}]")

        if level == "HIGH":
            high_impact.append((score, item, top))
            if italian:
                lines.append(
                    "- **Regola briefing**: riportare i fatti del titolo con [N]; "
                    "non sostituire con commenti generici di settore."
                )
            else:
                lines.append(
                    "- **Briefing rule**: report headline facts with [N]; "
                    "do not replace with generic sector commentary."
                )
        elif italian:
            lines.append("- Includere nel bullet strumento con citazione [N].")
        else:
            lines.append("- Include in the instrument bullet with citation [N].")

        lines.append("")

    if high_impact:
        _, dominant_item, dominant_headline = max(high_impact, key=lambda row: row[0])
        dominant_label = instrument_label(dominant_item)
        title = dominant_headline["title"]
        if italian:
            lines.insert(
                2,
                (
                    f"**Notizia dominante watchlist**: {dominant_label} — \"{title}\". "
                    "La **prima frase** del Sommario Esecutivo deve riportare questo evento "
                    "con [N] **prima** di leader/laggard 1D o macro."
                ),
            )
        else:
            lines.insert(
                2,
                (
                    f"**Dominant watchlist story**: {dominant_label} — \"{title}\". "
                    "The **first sentence** of the Executive Summary must report this event "
                    "with [N] **before** 1D leader/laggard or macro."
                ),
            )
        lines.insert(3, "")

    return "\n".join(lines).rstrip()


def _prefetch_limits(instrument_count: int) -> dict[str, int]:
    """Scale Serper prefetch down for larger watchlists to stay within LLM context."""
    if instrument_count >= 7:
        return {
            "max_local_queries": 2,
            "max_global_queries": 2,
            "max_nasdaq_queries": 2,
            "max_headlines_per_ticker": 8,
        }
    if instrument_count >= 5:
        return {
            "max_local_queries": 3,
            "max_global_queries": 3,
            "max_nasdaq_queries": 2,
            "max_headlines_per_ticker": 10,
        }
    return {
        "max_local_queries": 5,
        "max_global_queries": 5,
        "max_nasdaq_queries": 3,
        "max_headlines_per_ticker": 18,
    }


def prefetch_watchlist_news_bundle(
    instruments: list[dict[str, Any]],
    *,
    current_year: int | None = None,
    language: str = "English",
    start_citation: int = 7,
    max_local_queries: int = 5,
    max_global_queries: int = 5,
    max_headlines_per_ticker: int = 18,
) -> tuple[str, str, str, list[dict[str, Any]]]:
    """Return digest, material brief, reference seed markdown, and seed entries."""
    year = current_year or datetime.now(MILAN_TZ).year
    has_serper = bool(os.getenv("SERPER_API_KEY", "").strip())
    limits = _prefetch_limits(len(instruments))
    max_local_queries = limits["max_local_queries"]
    max_global_queries = limits["max_global_queries"]
    max_nasdaq_queries = limits["max_nasdaq_queries"]
    max_headlines_per_ticker = limits["max_headlines_per_ticker"]

    digest_lines = [
        "Pre-fetched headlines (deterministic). Ranked by structural relevance:",
        "recency, match on instrument name/ticker, source tier, document type.",
        "Tags: **OFFICIAL SOURCE** (Borsa Italiana news), **INSTITUTIONAL SOURCE**, "
        "**MATERIAL NEWS**.",
        "",
    ]

    headlines_by_ticker: dict[str, list[dict[str, str]]] = {}

    for item in instruments:
        ticker = item["ticker"]
        name = item["name"]
        digest_lines.append(f"### {name} ({ticker})")
        print(f"  Prefetch news: {ticker}...", flush=True)

        if not has_serper:
            digest_lines.append("- _Serper prefetch skipped (SERPER_API_KEY not set)._")

        combined = collect_instrument_headlines(
            item,
            current_year=year,
            max_local_queries=max_local_queries,
            max_global_queries=max_global_queries,
            max_nasdaq_queries=max_nasdaq_queries,
            max_headlines=max_headlines_per_ticker,
        )
        headlines_by_ticker[ticker] = combined

        if not combined:
            digest_lines.append("- _No headlines returned from Yahoo or Serper prefetch._")
        else:
            digest_lines.extend(
                _format_headline_line(item, headline) for headline in combined
            )

        digest_lines.append("")

    seed_markdown, seed_entries = build_research_reference_seed(
        instruments,
        headlines_by_ticker,
        start_citation=start_citation,
    )
    material_brief = build_material_news_brief(
        instruments,
        headlines_by_ticker,
        language=language,
        seed_entries=seed_entries,
    )
    return "\n".join(digest_lines).rstrip(), material_brief, seed_markdown, seed_entries


def prefetch_watchlist_news(
    instruments: list[dict[str, Any]],
    *,
    current_year: int | None = None,
    max_local_queries: int = 5,
    max_global_queries: int = 5,
    max_headlines_per_ticker: int = 18,
) -> str:
    """Build a markdown digest of pre-fetched Yahoo + Serper news per ticker."""
    digest, _, _, _ = prefetch_watchlist_news_bundle(
        instruments,
        current_year=current_year,
        max_local_queries=max_local_queries,
        max_global_queries=max_global_queries,
        max_headlines_per_ticker=max_headlines_per_ticker,
    )
    return digest
