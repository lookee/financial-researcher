"""Serper search tools with flexible argument parsing for LLM tool calls."""

from typing import Type

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


class SerperSearchTool(SerperDevTool):
    """General web search via Serper."""

    args_schema: Type[BaseModel] = FlexibleSerperArgs
    n_results: int = 12


class SerperNewsTool(SerperDevTool):
    """News search via Serper (news mode) — global/international coverage."""

    name: str = "Search recent financial news with Serper"
    description: str = (
        "Search recent news articles worldwide (news mode, no country filter). "
        "Use for international headlines: Reuters, Bloomberg, CNBC, MarketWatch, "
        "Financial Times, sector and macro news. Complement Italian/local searches. "
        "Always pass the query as search_query."
    )
    args_schema: Type[BaseModel] = FlexibleSerperArgs
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
