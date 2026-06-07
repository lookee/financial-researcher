# Acknowledgements

## Udemy course

This project builds on concepts and code patterns from:

**AI Engineer Agentic Track: The Complete Agent & MCP Course**  
Instructor: **[Ed Donner](https://www.udemy.com/user/ed-donner-3/)**  
Course URL: https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/

The course covers CrewAI, multi-agent workflows, tools, and MCP. The upstream course repository is [ed-donner/agents](https://github.com/ed-donner/agents). The `InstrumentCrew` structure (agents, tasks, sequential process, YAML configuration) follows that teaching material, extended here with:

- ISIN resolution via OpenFIGI and Yahoo Finance
- Deterministic market data and ETF holdings pipelines
- Stock vs ETF report templates with cited sections
- Local caching for identity and market snapshots
- CLI commands for watchlists and report refresh

## Third-party data

- **Yahoo Finance** (via `yfinance`) — market prices and fund holdings
- **OpenFIGI** — ISIN to ticker mapping
- **Serper** — news search for the news researcher agent
- **OpenAI** — LLM backend for CrewAI agents
