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


class SerperNewsTool(SerperDevTool):
    """News search via Serper (news mode)."""

    name: str = "Search recent financial news with Serper"
    description: str = (
        "Search recent news articles on the internet (news mode). "
        "Use for company and ETF headlines, sector news, earnings, M&A, "
        "and market updates. "
        "For Italian instruments (.MI) use Italian queries and sources "
        "(Il Sole 24 Ore, ANSA, Milano Finanza, Borsa Italiana). "
        "Prefer broad news searches over narrow corporate-action-only queries. "
        "Include the current year in the query when possible. "
        "Always pass the query as search_query."
    )
    args_schema: Type[BaseModel] = FlexibleSerperArgs
    search_type: str = "news"
