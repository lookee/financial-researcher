"""Serper search tools with flexible argument parsing for LLM tool calls."""

from __future__ import annotations

import json
from typing import Any, Type

import requests
from crewai_tools import SerperDevTool
from json_repair import repair_json
from pydantic import BaseModel, Field, model_validator

_MIN_QUERY_LEN = 12


class FlexibleSerperArgs(BaseModel):
    """Normalize common LLM argument mistakes before calling Serper."""

    search_query: str | None = Field(
        default=None,
        description="Mandatory search query for the internet or news search",
    )
    search_queries: list[str] | None = Field(
        default=None,
        description="Optional batch of search queries (one Serper call each)",
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
        if self.search_queries:
            cleaned = [
                query.strip()
                for query in self.search_queries
                if isinstance(query, str) and query.strip()
            ]
            if cleaned:
                self.search_queries = cleaned
                if not self.search_query:
                    self.search_query = cleaned[0]
                return self

        resolved = (self.search_query or self.query or self.description or "").strip()
        if not resolved:
            raise ValueError("search_query is required")
        self.search_query = resolved
        return self


def _looks_like_valid_query(query: str) -> bool:
    cleaned = query.strip()
    if len(cleaned) < _MIN_QUERY_LEN:
        return False
    if cleaned.startswith('\\"') or cleaned.startswith('",'):
        return False
    return any(char.isalpha() for char in cleaned)


def _extract_queries_from_items(items: list[Any]) -> list[str]:
    queries: list[str] = []
    seen: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            candidate = resolve_serper_search_query(item)
        elif isinstance(item, str):
            candidate = item.strip()
        else:
            continue
        if not candidate or not _looks_like_valid_query(candidate):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        queries.append(candidate)
    return queries


def _queries_to_kwargs(queries: list[str]) -> dict[str, Any]:
    if len(queries) == 1:
        return {"search_query": queries[0]}
    return {"search_queries": queries}


def _parse_tool_input(tool_input: str) -> Any | None:
    for loader in (json.loads, lambda raw: json.loads(repair_json(raw))):
        try:
            return loader(tool_input)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return None


def normalize_serper_tool_input(tool_input: str | None) -> dict[str, Any] | None:
    """Convert LLM tool inputs (including JSON arrays) into Serper kwargs."""
    if not tool_input or not isinstance(tool_input, str) or not tool_input.strip():
        return None

    parsed = _parse_tool_input(tool_input.strip())
    if parsed is None:
        return None

    if isinstance(parsed, dict):
        if "search_queries" in parsed or "search_query" in parsed:
            queries = _extract_queries_from_items([parsed])
            if queries:
                return _queries_to_kwargs(queries)
        nested = resolve_serper_search_query(parsed)
        if nested and _looks_like_valid_query(nested):
            return {"search_query": nested}
        return None

    if isinstance(parsed, list):
        queries = _extract_queries_from_items(parsed)
        if queries:
            return _queries_to_kwargs(queries)

    return None


def resolve_serper_search_query(kwargs: dict[str, Any]) -> str:
    """Resolve a Serper query from common LLM argument shapes."""
    batch = kwargs.get("search_queries")
    if isinstance(batch, list):
        for item in batch:
            if isinstance(item, str) and _looks_like_valid_query(item):
                return item.strip()

    for key in ("search_query", "query", "description"):
        raw = kwargs.get(key)
        if not isinstance(raw, str):
            continue
        cleaned = raw.strip()
        if not cleaned:
            continue
        if cleaned.startswith("[") and cleaned.endswith("]"):
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                parsed = _parse_tool_input(cleaned)
            if isinstance(parsed, list):
                queries = _extract_queries_from_items(parsed)
                if queries:
                    return queries[0]
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
        batch = kwargs.get("search_queries")
        if isinstance(batch, list) and len(batch) > 1:
            parts: list[str] = []
            for query in batch:
                if not isinstance(query, str) or not _looks_like_valid_query(query):
                    continue
                result = self._run_single(search_query=query.strip())
                parts.append(f"Query: {query.strip()}\n{result}")
            if parts:
                return "\n\n---\n\n".join(parts)
            return (
                "Serper search skipped: batch contained no valid search_query strings."
            )
        return self._run_single(**kwargs)

    def _run_single(self, **kwargs: Any) -> Any:
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


def apply_serper_tool_input_patch() -> None:
    """Accept JSON-array tool inputs that CrewAI otherwise rejects as non-dict."""
    from crewai.tools.tool_usage import ToolUsage

    original_validate = ToolUsage._validate_tool_input

    def _validate_tool_input(
        self: ToolUsage, tool_input: str | None
    ) -> dict[str, Any]:
        normalized = normalize_serper_tool_input(tool_input)
        if normalized is not None:
            return normalized
        return original_validate(self, tool_input)

    ToolUsage._validate_tool_input = _validate_tool_input


apply_serper_tool_input_patch()


class SerperSearchTool(FlexibleSerperTool):
    """General web search via Serper."""

    name: str = "Search web with Serper"
    description: str = (
        "General web search worldwide (no country filter). "
        "Use for global/English sources: Fed, BLS, US CPI, company IR in English, "
        "Reuters, Bloomberg. Write search_query in English. "
        "For Italian sites and Italy-focused topics, use Search Italian web with Serper "
        "with Italian query text instead."
    )
    n_results: int = 12


class SerperNewsTool(FlexibleSerperTool):
    """News search via Serper (news mode) — global/international coverage."""

    name: str = "Search recent financial news with Serper"
    description: str = (
        "Search recent news articles worldwide (news mode, no country filter). "
        "Use for **World / global** and **Issuer events (global)** queries: "
        "Reuters, Bloomberg, CNBC, MarketWatch, Financial Times, US sector news. "
        "Write search_query in English. "
        "For Italian/local headlines and Italian institutional sites, use "
        "Search Italian financial news with Serper with Italian query text instead. "
        "Pass search_query as a single string, or a JSON array of {search_query: ...} "
        "objects (one query per item)."
    )
    search_type: str = "news"
    n_results: int = 15


class SerperNewsItalyTool(SerperNewsTool):
    """News search biased to Italian sources (gl=it, hl=it)."""

    name: str = "Search Italian financial news with Serper"
    description: str = (
        "Search recent Italian/local financial news (news mode, gl=it, hl=it). "
        "Use for **Italy / local** and **Issuer events (Italy)** queries: .MI stocks "
        "and ETFs, Borsa Italiana, CONSOB, Il Sole 24 Ore, ANSA, Milano Finanza. "
        "Write search_query in Italian (e.g. notizie, utili, comunicato, borsa). "
        "Do NOT use this tool for English/global or NASDAQ queries. "
        "Pass search_query as one plain string per call; if batching, use a JSON "
        "array of {search_query: ...} objects."
    )
    country: str = "it"
    locale: str = "it"
    n_results: int = 15


class SerperSearchItalyTool(FlexibleSerperTool):
    """Web search biased to Italian sources (gl=it, hl=it)."""

    name: str = "Search Italian web with Serper"
    description: str = (
        "General web search with Italy locale (gl=it, hl=it). "
        "Use for official Italian portals and Italy-focused macro research: "
        "Borsa Italiana, CONSOB, Banca d'Italia, ECB/BCE (Italian pages), "
        "Eurostat, calendario eventi in Italia. "
        "Write search_query in Italian. "
        "For Fed, US BLS, US earnings and global English sources, use "
        "Search recent financial news with Serper or Search web with Serper instead."
    )
    country: str = "it"
    locale: str = "it"
    n_results: int = 12


class SerperNasdaqNewsTool(SerperNewsTool):
    """News search biased to NASDAQ.com and US market coverage."""

    name: str = "Search NASDAQ news with Serper"
    description: str = (
        "Search recent NASDAQ.com and US market news (news mode, US locale). "
        "Use for **NASDAQ / US** queries in stock_news_queries and etf_news_queries, "
        "especially thematic ETFs (semiconductors, AI, biotech). "
        "Queries often include site:nasdaq.com. Pass search_query as one string, "
        "or a JSON array of {search_query: ...} objects."
    )
    country: str = "us"
    locale: str = "en"
    n_results: int = 12
