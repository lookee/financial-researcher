"""Serper news search tool configured for financial news queries."""

from crewai_tools import SerperDevTool


class SerperNewsTool(SerperDevTool):
    name: str = "Search recent financial news with Serper"
    description: str = (
        "Search recent news articles on the internet (news mode). "
        "Use for company and ETF headlines, sector news, earnings, M&A, "
        "and market updates. "
        "For Italian instruments (.MI) use Italian queries and sources "
        "(Il Sole 24 Ore, ANSA, Milano Finanza, Borsa Italiana). "
        "Prefer broad news searches over narrow corporate-action-only queries. "
        "Include the current year in the query when possible."
    )
    search_type: str = "news"
