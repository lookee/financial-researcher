"""Structural headline ranking for watchlist news — no hardcoded topic keywords."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from financial_researcher.services.watchlist_context import _search_name

MILAN_TZ = ZoneInfo("Europe/Rome")

MATERIALITY_THRESHOLD = 45
HIGH_IMPACT_SCORE = 70

OFFICIAL_DOMAINS: tuple[str, ...] = (
    "borsaitaliana.it",
    "consob.it",
    "bancaditalia.it",
    "abi.it",
    "bafin.de",
    "deutsche-boerse.com",
    "esma.europa.eu",
    "nasdaq.com",
)

EXCHANGE_NEWS_PATHS: tuple[str, ...] = (
    "/comunicati",
    "teleborsa",
    "/avvisi",
    "/documenti",
    "/news/",
)

STATIC_DOCUMENT_PATHS: tuple[str, ...] = (
    "/pubblicazioni/",
    "/publications/",
    "/rapporto",
    "/annual",
    "/archive/",
    "/static/",
)


def instrument_search_tokens(item: dict[str, Any]) -> list[str]:
    """Build per-instrument match tokens from name and ticker (no fixed topic words)."""
    ticker = item["ticker"].upper()
    base = ticker.split(".")[0]
    short_name = _search_name(item["name"])

    tokens: list[str] = [ticker.lower(), base.lower(), short_name.lower()]
    for word in short_name.split():
        cleaned = word.strip(".,;:").lower()
        if len(cleaned) >= 4:
            tokens.append(cleaned)

    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token and token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


def headline_age_days(
    headline: dict[str, str],
    *,
    today: datetime | None = None,
) -> int | None:
    raw = (headline.get("date") or "").strip()
    if len(raw) >= 10 and raw[4] == "-":
        try:
            published = datetime.strptime(raw[:10], "%Y-%m-%d").date()
            ref = (today or datetime.now(MILAN_TZ)).date()
            return (ref - published).days
        except ValueError:
            return None
    return None


def recency_score(headline: dict[str, str]) -> int:
    age = headline_age_days(headline)
    if age is None:
        return 0
    if age <= 3:
        return 30
    if age <= 7:
        return 22
    if age <= 14:
        return 10
    if age > 60:
        return -30
    if age > 30:
        return -12
    return 0


def issuer_match_score(item: dict[str, Any], headline: dict[str, str]) -> int:
    """Score how specifically the headline relates to this instrument."""
    title = (headline.get("title") or "").lower()
    blob = f"{title} {headline.get('summary', '')}".lower()
    url = (headline.get("url") or "").lower()
    tokens = instrument_search_tokens(item)

    title_hits = sum(1 for token in tokens if token in title)
    if title_hits >= 2:
        score = 35
    elif title_hits == 1:
        score = 22
    else:
        score = 0

    body_hits = sum(1 for token in tokens if token in blob or token in url)
    score += min(body_hits * 4, 16)

    if score == 0:
        score -= 20
    return score


def source_tier_score(headline: dict[str, str]) -> int:
    """Prefer exchange/regulator primary sources over generic pages."""
    url = (headline.get("url") or "").lower()
    if not url:
        return 0

    domain = urlparse(url).netloc.lower()
    if "borsaitaliana.it" in domain:
        score = 28
        if any(segment in url for segment in EXCHANGE_NEWS_PATHS):
            score += 22
        return score
    if "consob.it" in domain:
        return 22
    if "deutsche-boerse.com" in domain or "bafin.de" in domain:
        return 18
    if "bancaditalia.it" in domain:
        return 6
    if "nasdaq.com" in domain:
        return 14
    if any(domain.endswith(off) or off in domain for off in OFFICIAL_DOMAINS):
        return 12
    return 0


def document_form_penalty(headline: dict[str, str]) -> int:
    """Penalise static reports/PDFs versus time-sensitive news pages."""
    url = (headline.get("url") or "").lower()
    if not url:
        return 0
    if url.endswith(".pdf"):
        return -35
    if any(segment in url for segment in STATIC_DOCUMENT_PATHS):
        return -28
    return 0


def is_official_source(headline: dict[str, str]) -> bool:
    url = (headline.get("url") or "").lower()
    return any(domain in url for domain in OFFICIAL_DOMAINS)


def is_exchange_news(headline: dict[str, str]) -> bool:
    url = (headline.get("url") or "").lower()
    return "borsaitaliana.it" in url and any(
        segment in url for segment in EXCHANGE_NEWS_PATHS
    )


def headline_relevance_score(item: dict[str, Any], headline: dict[str, str]) -> int:
    """Composite relevance score using structure + instrument identity only."""
    score = issuer_match_score(item, headline)
    score += recency_score(headline)
    score += source_tier_score(headline)
    score += document_form_penalty(headline)

    if headline.get("issuer_event"):
        score += 12
    if headline.get("region") == "Yahoo":
        score += 10
    if headline.get("region") == "Serper NASDAQ":
        score += 6

    return score


def impact_level(item: dict[str, Any], headline: dict[str, str]) -> str:
    score = headline_relevance_score(item, headline)
    age = headline_age_days(headline)

    if score >= HIGH_IMPACT_SCORE:
        return "ALTA"
    if (
        item.get("type") == "stock"
        and is_exchange_news(headline)
        and age is not None
        and age <= 14
        and issuer_match_score(item, headline) >= 20
    ):
        return "ALTA"
    if score >= MATERIALITY_THRESHOLD:
        return "MEDIA"
    return "BASSA"
