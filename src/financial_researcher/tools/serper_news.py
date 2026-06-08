"""Serper search tools with flexible argument parsing for LLM tool calls."""

from __future__ import annotations

import json
from typing import Any, Type

import requests
from crewai_tools import SerperDevTool
from pydantic import BaseModel, Field, model_validator


class FlexibleSerperArgs(BaseModel):
    """Normalize common LLM argument mistakes before calling Serper."""

    search_query: str | None = Field(
        default=None,
        description="Mandatory search query for the internet or news search",
    )
    query: str | None = Field(
        default=None,
        description="Alternative key for search_query",
    )
    description: str | None = Field(
        default=None,
        description="Search query text when search_query is omitted",
    )

    @model_validator(mode="after")
    def normalize_search_query(self) -> "FlexibleSerperArgs":
        resolved = (self.search_query or self.query or self.description or "").strip()
        if not resolved:
            raise ValueError("search_query is required")
        self.search_query = resolved
        return self


def resolve_serper_search_query(kwargs: dict[str, Any]) -> str:
    """Resolve a Serper query from common LLM argument shapes."""
    for key in ("search_query", "query", "description"):
        raw = kwargs.get(key)
        if not isinstance(raw, str):
            continue
        cleaned = raw.strip()
        if not cleaned:
            continue
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                return cleaned
            if isinstance(parsed, dict):
                nested = resolve_serper_search_query(parsed)
                if nested:
                    return nested
            return cleaned
        return cleaned
    return ""


class FlexibleSerperTool(SerperDevTool):
    """SerperDevTool wrapper that tolerates LLM argument mistakes."""

    args_schema: Type[BaseModel] = FlexibleSerperArgs

    def _run(self, **kwargs: Any) -> Any:
        search_query = resolve_serper_search_query(kwargs)
        if not search_query:
            return (
                "Serper search skipped: missing or empty search_query. "
                "Pass one plain query string (company name, ticker, or site: filter) "
                "as search_query."
            )
        try:
            return super()._run(search_query=search_query)
        except requests.exceptions.HTTPError as exc:
            response = getattr(exc, "response", None)
            if response is not None and response.status_code == 400:
                detail = (response.text or "").strip()[:500]
                return (
                    f"Serper news search failed (400 Bad Request) for query: "
                    f"{search_query!r}. API message: {detail or 'Missing query parameter'}. "
                    "Retry with a shorter plain-text query."
                )
            raise


class SerperSearchTool(FlexibleSerperTool):
    """General web search via Serper."""

    n_results: int = 12


class SerperNewsTool(FlexibleSerperTool):
    """News search via Serper (news mode) — global/international coverage."""

    name: str = "Search recent financial news with Serper"
    description: str = (
        "Search recent news articles worldwide (news mode, no country filter). "
        "Use for international headlines: Reuters, Bloomberg, CNBC, MarketWatch, "
        "Financial Times, sector and macro news. Complement Italian/local searches. "
        "Always pass the query as search_query."
    )
    search_type: str = "news"
    n_results: int = 15


class SerperNewsItalyTool(SerperNewsTool):
    """News search biased to Italian sources (gl=it, hl=it)."""

    name: str = "Search Italian financial news with Serper"
    description: str = (
        "Search recent Italian/local financial news (news mode, Italy locale). "
        "Use for .MI stocks and ETFs, Borsa Italiana, Il Sole 24 Ore, ANSA, "
        "Milano Finanza. Pair with global Serper searches for full coverage. "
        "Always pass search_query."
    )
    country: str = "it"
    locale: str = "it"
    n_results: int = 15


class SerperNasdaqNewsTool(SerperNewsTool):
    """News search biased to NASDAQ.com and US market coverage."""

    name: str = "Search NASDAQ news with Serper"
    description: str = (
        "Search recent NASDAQ.com and US market news (news mode, US locale). "
        "Use for **NASDAQ / US** queries in stock_news_queries and etf_news_queries, "
        "especially thematic ETFs (semiconductors, AI, biotech). "
        "Queries often include site:nasdaq.com. Always pass search_query."
    )
    country: str = "us"
    locale: str = "en"
    n_results: int = 12
