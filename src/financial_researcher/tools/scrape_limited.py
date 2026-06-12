"""Optional scrape truncation to limit token use from website tools."""

from __future__ import annotations

import re
from typing import Any

from crewai_tools import ScrapeWebsiteTool

from financial_researcher.settings import get_scrape_settings

DEFAULT_MAX_CHARS = 2500
TRUNCATION_SUFFIX = "[...troncato]"


def truncate_scraped_text(
    text: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    keywords: list[str] | None = None,
) -> str:
    """Reduce scraped text to *max_chars*, preferring paragraphs that match *keywords*."""
    cleaned = text.strip()
    if not cleaned or len(cleaned) <= max_chars:
        return cleaned

    reserved = max_chars - len(TRUNCATION_SUFFIX) - 1
    if reserved < 200:
        reserved = max_chars

    tokens = [token.lower() for token in (keywords or []) if token and len(token) >= 2]
    paragraphs = _split_paragraphs(cleaned)

    if tokens:
        ranked = sorted(
            paragraphs,
            key=lambda paragraph: _paragraph_score(paragraph, tokens),
            reverse=True,
        )
        selected: list[str] = []
        used = 0
        for paragraph in ranked:
            if _paragraph_score(paragraph, tokens) <= 0:
                break
            chunk = paragraph.strip()
            if not chunk:
                continue
            if used + len(chunk) + (2 if selected else 0) > reserved:
                remaining = reserved - used - (2 if selected else 0)
                if remaining > 80:
                    selected.append(chunk[:remaining].rstrip())
                    used = reserved
                break
            selected.append(chunk)
            used += len(chunk) + (2 if len(selected) > 1 else 0)
        if selected:
            body = "\n\n".join(selected)
            if len(body) > reserved:
                body = body[:reserved].rstrip()
            return f"{body} {TRUNCATION_SUFFIX}"

    body = cleaned[:reserved].rstrip()
    return f"{body} {TRUNCATION_SUFFIX}"


def _split_paragraphs(text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    if len(chunks) > 1:
        return chunks
    return [line.strip() for line in text.split("\n") if line.strip()]


def _paragraph_score(paragraph: str, keywords: list[str]) -> int:
    lowered = paragraph.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def _extract_keywords(kwargs: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    for key in ("keywords", "search_query", "query", "description"):
        raw = kwargs.get(key)
        if isinstance(raw, str) and raw.strip():
            keywords.extend(re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]{1,}", raw))
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str) and item.strip():
                    keywords.append(item.strip())

    url = kwargs.get("website_url") or ""
    if isinstance(url, str) and url:
        keywords.extend(re.findall(r"[A-Za-z]{2,}", url.split("/")[-1]))

    seen: set[str] = set()
    unique: list[str] = []
    for keyword in keywords:
        token = keyword.lower()
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


class LimitedScrapeWebsiteTool(ScrapeWebsiteTool):
    """ScrapeWebsiteTool that truncates long pages before returning to the agent."""

    max_chars: int = DEFAULT_MAX_CHARS

    def _run(self, **kwargs: Any) -> Any:
        text = super()._run(**kwargs)
        if not isinstance(text, str):
            return text
        return truncate_scraped_text(
            text,
            max_chars=self.max_chars,
            keywords=_extract_keywords(kwargs),
        )


def build_scrape_tool() -> ScrapeWebsiteTool:
    """Return a scrape tool respecting defaults/settings.yaml scrape.truncate_enabled."""
    settings = get_scrape_settings()
    if settings["truncate_enabled"]:
        return LimitedScrapeWebsiteTool(max_chars=settings["max_chars"])
    return ScrapeWebsiteTool()
