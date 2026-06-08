"""CrewAI crew for unified watchlist executive briefings.

Agent/task layout follows CrewAI patterns from Ed Donner's Udemy course:
https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.tools.base_tool import Tool
from crewai_tools import ScrapeWebsiteTool
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool

from financial_researcher.tools.serper_news import (
    SerperNewsItalyTool,
    SerperNewsTool,
    SerperSearchTool,
)

_SEARCH_TOOLS = [
    SerperSearchTool(),
    SerperNewsTool(),
    ScrapeWebsiteTool(),
]

_NEWS_TOOLS = [
    SerperNewsTool(),
    SerperNewsItalyTool(),
    SerperSearchTool(),
    ScrapeWebsiteTool(),
]


@CrewBase
class WatchlistBriefingCrew:
    """Four analysts in parallel, then chief strategist executive briefing."""

    agents_config = "config/agents_briefing.yaml"
    tasks_config = "config/tasks_briefing.yaml"

    @agent
    def market_analyst(self) -> Agent:
        """Analyses pre-loaded watchlist market data."""
        return Agent(
            config=self.agents_config["market_analyst"],
            verbose=True,
        )

    @agent
    def news_analyst(self) -> Agent:
        """Collects recent news; citations start after Yahoo market data."""
        return Agent(
            config=self.agents_config["news_analyst"],
            verbose=True,
            tools=[
                *_NEWS_TOOLS,
                Tool.from_langchain(YahooFinanceNewsTool().as_tool()),
            ],
        )

    @agent
    def outlook_analyst(self) -> Agent:
        """Medium-term macro and thematic outlook."""
        return Agent(
            config=self.agents_config["outlook_analyst"],
            verbose=True,
            tools=_SEARCH_TOOLS,
        )

    @agent
    def calendar_analyst(self) -> Agent:
        """Upcoming events and catalysts calendar."""
        return Agent(
            config=self.agents_config["calendar_analyst"],
            verbose=True,
            tools=_SEARCH_TOOLS,
        )

    @agent
    def chief_strategist(self) -> Agent:
        """Writes the final executive watchlist briefing."""
        return Agent(
            config=self.agents_config["chief_strategist"],
            verbose=True,
        )

    @task
    def market_analysis_task(self) -> Task:
        return Task(config=self.tasks_config["market_analysis_task"])

    @task
    def news_analysis_task(self) -> Task:
        return Task(config=self.tasks_config["news_analysis_task"])

    @task
    def outlook_analysis_task(self) -> Task:
        return Task(config=self.tasks_config["outlook_analysis_task"])

    @task
    def calendar_analysis_task(self) -> Task:
        return Task(config=self.tasks_config["calendar_analysis_task"])

    @task
    def executive_briefing_task(self) -> Task:
        return Task(config=self.tasks_config["executive_briefing_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
