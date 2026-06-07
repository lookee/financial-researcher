# Financial Researcher

![Python](https://img.shields.io/badge/python-3.10--3.12-3776AB?logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-8957E5?logo=openai&logoColor=white)
![Status](https://img.shields.io/badge/status-experimental-red)

Financial Researcher is a command-line application that produces structured Markdown research reports for **stocks and ETFs** starting from an **ISIN** code. Market data, instrument identity, and report scaffolding are resolved deterministically in Python; a small [CrewAI](https://crewai.com) crew handles news gathering and final report writing.

## Requirements

- Python 3.10–3.12
- [uv](https://github.com/astral-sh/uv) (recommended)
- API keys: OpenAI, Serper (see Setup below)

## Setup

```bash
pip install uv
uv sync
cp .env.sample .env
# Set OPENAI_API_KEY and SERPER_API_KEY in .env
```

## Usage

```bash
# Stock report
uv run report US67066G1040 NVDA

# ETF report
uv run report IE00BK5BQT80 VWCE.DE

# ISIN only (uses cached identity when available)
uv run report US67066G1040

# Resolve and cache instrument identity
uv run resolve US67066G1040 NVDA

# Batch run from watchlist.yaml
uv run watchlist

# Regenerate reports for ISINs already present under output/reports/
uv run refresh-reports
```

Optional flags: `--force`, `--type stock|etf`.

## Overview

The pipeline resolves the instrument (OpenFIGI, Yahoo Finance), fetches a cached market snapshot (prices, performance, fundamentals, ETF top holdings), pre-formats cited data sections, then runs two LLM agents in sequence. The result is a single Markdown file with numbered references, separate templates for stocks and ETFs, and explicit data-limitation notes.

**Experimental project** — intended for learning and exploration, not production use. See [Disclaimer](#disclaimer).

## Agents

The crew runs **sequentially** (`Process.sequential`): the news researcher completes its task before the report composer starts. Both agents use **OpenAI GPT-4o mini** (`openai/gpt-4o-mini`).

### 1. `news_researcher` — Financial News Researcher

| | |
|---|---|
| **Task** | Collect recent, verifiable news and events for the target instrument |
| **Tools** | [Serper](https://serper.dev) web & news search, Yahoo Finance news, optional website scraping for issuer/IR pages |
| **Input** | Company name, ticker, ISIN, pre-loaded `market_context` (read-only) |
| **Output** | News brief with titled items, dates, summaries, and numbered citations |

**Behaviour**

- Focuses on the **last 72 hours**; does not re-fetch prices already present in market data
- Assigns citation **`[1]`** to Yahoo Finance (reserved by the pipeline); new sources start at **`[2]`**
- Cites every fact; omits unsupported claims
- Surfaces risks or opportunities **only when mentioned in sources**

### 2. `report_composer` — Financial Instrument Report Writer

| | |
|---|---|
| **Task** | Assemble the final Markdown report in the configured language |
| **Tools** | None — relies on pre-loaded data and the news researcher output |
| **Input** | `identity_context`, `market_summary` (pre-formatted sections), news task output |
| **Output** | Complete report written to `output/reports/` |

**Behaviour**

- Copies pre-formatted market sections from `market_summary` **verbatim** (key metrics, performance, ETF top holdings, data limitations)
- Applies the **stock** or **ETF** template based on `instrument_type`
- Writes the news section from the news researcher; includes risks only when cited
- Produces a numbered **References** section; does not issue buy/sell/hold recommendations

Agent definitions: [`agents_instrument.yaml`](src/financial_researcher/config/agents_instrument.yaml) · Task definitions: [`tasks_instrument.yaml`](src/financial_researcher/config/tasks_instrument.yaml)

## Pipeline

```
ISIN + ticker
    │
    ├─ IsinResolver          OpenFIGI → cached identity
    ├─ MarketDataService     Yahoo Finance → cached snapshot
    └─ report_builder        pre-formatted market_summary  →  citation [1]
            │
            ▼
    CrewAI (sequential)
    ├─ news_researcher       Serper, Yahoo News, scrape  →  citations [2+]
    └─ report_composer       final Markdown report
```

## Report language

Default: **English**.

- Global default: `default_language` in [`settings.yaml`](src/financial_researcher/config/settings.yaml)
- Override via `.env`: `REPORT_LANGUAGE=Italian`
- Per run: `uv run report US67066G1040 NVDA --language Italian`

## Output

| Path | Description |
|------|-------------|
| `output/reports/{ISIN}_{TICKER}_{DATE}.md` | Generated report (local, gitignored) |
| `data/identity/{ISIN}.json` | Cached instrument identity |
| `data/market/{ISIN}/latest.json` | Cached market snapshot (1 h TTL) |

The `output/` directory is not tracked by git.

## Sample reports

Static examples in [`examples/reports/`](examples/reports/) (2026-06-07):

| Instrument | Type | Report |
|------------|------|--------|
| NVIDIA Corporation (NVDA) | Stock | [US67066G1040_NVDA_2026-06-07.md](examples/reports/US67066G1040_NVDA_2026-06-07.md) |
| L&G Artificial Intelligence UCITS ETF (AIAI.MI) | ETF | [IE00BK5BCD43_AIAI_MI_2026-06-07.md](examples/reports/IE00BK5BCD43_AIAI_MI_2026-06-07.md) |
| VanEck Semiconductor UCITS ETF (SMH.MI) | ETF | [IE00BMC38736_SMH_MI_2026-06-07.md](examples/reports/IE00BMC38736_SMH_MI_2026-06-07.md) |

## Acknowledgements

This project extends CrewAI patterns from **Ed Donner's** Udemy course:

**[AI Engineer Agentic Track: The Complete Agent & MCP Course](https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/)**

Thank you to **Ed Donner** for the excellent agentic AI engineering course. See [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md) for details.

## Author

**Luca Amore** — [GitHub](https://github.com/lookee) · [lucaamore.com](https://www.lucaamore.com) · [LinkedIn](https://www.linkedin.com/in/lucaamore)

This code is free to use, copy, modify, and redistribute without restrictions.

## Disclaimer

**Experimental software.** Developed as an extension of agentic AI coursework. Not audited or intended for production.

**No warranty.** Provided *as is* without guarantees of correctness, completeness, or fitness for any purpose.

**Not financial advice.** Reports are for informational and educational use only. Market data and LLM output may be incomplete or incorrect. Verify against primary sources before any investment decision.

**Your responsibility.** You are responsible for API costs, third-party terms of service, and any use of generated output.

## License

Released into the **public domain**. See [LICENSE](LICENSE).
