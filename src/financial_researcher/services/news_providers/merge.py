"""Cross-provider headline deduplication."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize URLs for dedup (strip tracking, lang variants, trailing slash)."""
    cleaned = (url or "").strip()
    if not cleaned:
        return ""

    parsed = urlparse(cleaned.lower())
    query = parse_qs(parsed.query, keep_blank_values=False)
    for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "lang"):
        query.pop(key, None)
    filtered_query = urlencode(
        sorted((key, values[0]) for key, values in query.items() if values),
        doseq=False,
    )
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", filtered_query, ""))


def dedupe_headlines(items: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop duplicate headlines by normalized URL or identical title."""
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict[str, str]] = []

    for item in items:
        url_key = normalize_url(item.get("url") or "")
        title_key = (item.get("title") or "").strip().lower()
        if url_key:
            if url_key in seen_urls:
                continue
            seen_urls.add(url_key)
        elif title_key:
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
        else:
            continue
        unique.append(item)

    return unique
