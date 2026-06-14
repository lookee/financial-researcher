"""CrewAI crew for unified watchlist executive briefings.

Agent/task layout follows CrewAI patterns from Ed Donner's Udemy course:
https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/
"""

from financial_researcher.cli_output import configure_clean_cli_output, crew_verbose_enabled

configure_clean_cli_output()

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from financial_researcher import llm_compat  # noqa: F401 — patch LLM before agents run
from financial_researcher.agent_llm import build_agent_llm
from financial_researcher.services.llm_model_tracker import ensure_llm_model_tracker_installed

ensure_llm_model_tracker_installed()

from financial_researcher.tools.scrape_limited import build_scrape_tool
from financial_researcher.tools.serper_news import (
    SerperNasdaqNewsTool,
    SerperNewsItalyTool,
    SerperNewsTool,
    SerperSearchTool,
)

_SCRAPE_TOOL = build_scrape_tool()

_SEARCH_TOOLS = [
    SerperSearchTool(),
    SerperNewsTool(),
    _SCRAPE_TOOL,
]

_NEWS_TOOLS = [
    SerperNewsTool(),
    SerperNewsItalyTool(),
    SerperNasdaqNewsTool(),
    SerperSearchTool(),
    _SCRAPE_TOOL,
]


@CrewBase
class WatchlistBriefingCrew:
    """Four analysts in parallel, then chief strategist executive briefing."""

    agents_config = "defaults/agents_briefing.yaml"
    tasks_config = "defaults/tasks_briefing.yaml"

    @agent
    def market_analyst(self) -> Agent:
        """Analyses pre-loaded watchlist market data."""
        return Agent(
            config=self.agents_config["market_analyst"],
            llm=build_agent_llm("market"),
            verbose=crew_verbose_enabled(),
        )

    @agent
    def news_analyst(self) -> Agent:
        """Collects recent news; citations start after Yahoo market data."""
        return Agent(
            config=self.agents_config["news_analyst"],
            llm=build_agent_llm("news"),
            verbose=crew_verbose_enabled(),
            tools=_NEWS_TOOLS,
        )

    @agent
    def outlook_analyst(self) -> Agent:
        """Medium-term macro and thematic outlook."""
        return Agent(
            config=self.agents_config["outlook_analyst"],
            llm=build_agent_llm("outlook"),
            verbose=crew_verbose_enabled(),
            tools=_SEARCH_TOOLS,
        )

    @agent
    def calendar_analyst(self) -> Agent:
        """Upcoming events and catalysts calendar."""
        return Agent(
            config=self.agents_config["calendar_analyst"],
            llm=build_agent_llm("calendar"),
            verbose=crew_verbose_enabled(),
            tools=_SEARCH_TOOLS,
        )

    @agent
    def chief_strategist(self) -> Agent:
        """Writes the final executive watchlist briefing."""
        return Agent(
            config=self.agents_config["chief_strategist"],
            llm=build_agent_llm("chief"),
            verbose=crew_verbose_enabled(),
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
        return Task(
            config=self.tasks_config["executive_briefing_task"],
            context=[
                self.market_analysis_task(),
                self.news_analysis_task(),
                self.outlook_analysis_task(),
                self.calendar_analysis_task(),
            ],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=crew_verbose_enabled(),
        )
