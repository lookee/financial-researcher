"""Serper news search tool configured for financial news queries."""

from crewai_tools import SerperDevTool


class SerperNewsTool(SerperDevTool):
    name: str = "Search recent financial news with Serper"
    description: str = (
        "Search recent news articles on the internet. "
        "Use for company news, earnings releases and market updates. "
        "Include the current year in the query when possible."
    )
    search_type: str = "news"
