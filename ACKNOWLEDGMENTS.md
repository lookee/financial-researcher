# Acknowledgements

## Udemy course

This project builds on concepts and code patterns from:

**AI Engineer Agentic Track: The Complete Agent & MCP Course**  
Instructor: **[Ed Donner](https://www.udemy.com/user/ed-donner-3/)**  
Course URL: https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/

The course covers CrewAI, multi-agent workflows, tools, and MCP. The upstream course repository is [ed-donner/agents](https://github.com/ed-donner/agents). The `WatchlistBriefingCrew` structure (agents, tasks, sequential process, YAML configuration) follows that teaching material, extended here with:

- ISIN resolution via OpenFIGI and Yahoo Finance
- Deterministic market data pipelines for watchlist instruments
- Milan session scheduling (Europe/Rome)
- Unified executive briefing output with cited sections
- Local caching for identity and market snapshots

## Third-party data

- **Yahoo Finance** (via `yfinance`) — market prices and fund data
- **OpenFIGI** — ISIN to ticker mapping
- **Serper** — news search for the news analyst agent
- **OpenAI** — LLM backend for CrewAI agents
