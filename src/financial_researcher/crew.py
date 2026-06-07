"""CrewAI crew definition for ISIN-based instrument reports.

Agent/task layout follows the CrewAI project structure taught in Ed Donner's
Udemy course: https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/
"""

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.tools.base_tool import Tool
from crewai_tools import ScrapeWebsiteTool, SerperDevTool
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool

from financial_researcher.tools.serper_news import SerperNewsTool


@CrewBase
class InstrumentCrew:
    """Two-agent sequential crew: news research, then report composition."""

    agents_config = "config/agents_instrument.yaml"
    tasks_config = "config/tasks_instrument.yaml"

    @agent
    def news_researcher(self) -> Agent:
        """Collects recent news; citations start at [2] ([1] is Yahoo market data)."""
        return Agent(
            config=self.agents_config["news_researcher"],
            verbose=True,
            tools=[
                SerperDevTool(),
                SerperNewsTool(),
                ScrapeWebsiteTool(),
                Tool.from_langchain(YahooFinanceNewsTool().as_tool()),
            ],
        )

    @agent
    def report_composer(self) -> Agent:
        """Assembles the final Markdown report from pre-loaded data and news output."""
        return Agent(
            config=self.agents_config["report_composer"],
            verbose=True,
        )

    @task
    def news_research_task(self) -> Task:
        return Task(config=self.tasks_config["news_research_task"])

    @task
    def compose_report_task(self) -> Task:
        return Task(config=self.tasks_config["compose_report_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
