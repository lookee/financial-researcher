# Financial Researcher

![Python](https://img.shields.io/badge/python-3.10--3.12-3776AB?logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-8957E5?logo=openai&logoColor=white)
![Status](https://img.shields.io/badge/status-experimental-red)

CLI tool that generates cited Markdown research reports for **stocks and ETFs** from an **ISIN** code, using deterministic market-data pipelines and a two-agent [CrewAI](https://crewai.com) workflow.

## Requirements

| Requirement | Details |
|-------------|---------|
| Python | 3.10 – 3.12 |
| Package manager | [uv](https://github.com/astral-sh/uv) (recommended) |
| API keys | `OPENAI_API_KEY`, `SERPER_API_KEY` — see Setup |

## Setup

```bash
pip install uv
uv sync
cp .env.sample .env
```

Edit `.env` and set your API keys. Optional: `OPENFIGI_API_KEY` for higher OpenFIGI rate limits; `REPORT_LANGUAGE` to override the default report language.

## Usage

### Commands

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

# Regenerate reports for ISINs already under output/reports/
uv run refresh-reports
```

### Options

| Flag | Description |
|------|-------------|
| `--force` | Refresh cached identity and market data |
| `--type stock\|etf` | Force instrument type when resolving |
| `--language LANG` | Report language for a single run (default: English) |

### Report language

Default: **English**. Configure globally in [`settings.yaml`](src/financial_researcher/config/settings.yaml) (`default_language`) or via `.env` (`REPORT_LANGUAGE=Italian`).

---

## How it works

### Overview

Financial Researcher combines a **deterministic data layer** with a **sequential agent crew**:

1. **Resolve** the instrument from ISIN (OpenFIGI, Yahoo Finance) and cache identity.
2. **Fetch** a market snapshot — prices, performance, fundamentals, ETF top holdings — with a 1-hour cache.
3. **Pre-format** cited market sections in Python (`report_builder`); Yahoo Finance is always reference **`[1]`**.
4. **Run agents** — news research, then report composition — to produce a single Markdown file with numbered references, stock/ETF-specific templates, and explicit data-limitations.

> **Note:** Experimental software for learning and exploration, not production use. See [Disclaimer](#disclaimer).

### Pipeline

```
ISIN + ticker
    │
    ├─ IsinResolver          OpenFIGI → cached identity
    ├─ MarketDataService     Yahoo Finance → cached snapshot
    └─ report_builder        pre-formatted market_summary  →  [1]
            │
            ▼
    CrewAI (sequential)
    ├─ news_researcher       Serper, Yahoo News, scrape  →  [2+]
    └─ report_composer       final Markdown report
```

### Agents

Both agents use **OpenAI GPT-4o mini**. The news researcher finishes before the composer starts.

#### `news_researcher` — Financial News Researcher

| | |
|---|---|
| **Purpose** | Collect recent, verifiable news and events |
| **Tools** | [Serper](https://serper.dev) search & news, Yahoo Finance news, website scraping (issuer/IR pages) |
| **Scope** | Last **72 hours**; does not duplicate prices from market data |
| **Citations** | New sources from **`[2]`** onward (`[1]` reserved for Yahoo Finance) |

#### `report_composer` — Financial Instrument Report Writer

| | |
|---|---|
| **Purpose** | Assemble the final report in the configured language |
| **Tools** | None — uses pre-loaded data and the news task output |
| **Templates** | Separate layouts for **stock** and **ETF** instruments |
| **Constraints** | Copies market sections verbatim; cites every statement; no buy/sell/hold advice |

Configuration: [`agents_instrument.yaml`](src/financial_researcher/config/agents_instrument.yaml) · [`tasks_instrument.yaml`](src/financial_researcher/config/tasks_instrument.yaml)

## Output

| Path | Description |
|------|-------------|
| `output/reports/{ISIN}_{TICKER}_{DATE}.md` | Generated report (local, gitignored) |
| `data/identity/{ISIN}.json` | Cached instrument identity |
| `data/market/{ISIN}/latest.json` | Cached market snapshot (1 h TTL) |

## Sample reports

Examples in [`examples/reports/`](examples/reports/) (2026-06-07):

| Instrument | Type | Report |
|------------|------|--------|
| NVIDIA Corporation (NVDA) | Stock | [US67066G1040_NVDA_2026-06-07.md](examples/reports/US67066G1040_NVDA_2026-06-07.md) |
| L&G Artificial Intelligence UCITS ETF (AIAI.MI) | ETF | [IE00BK5BCD43_AIAI_MI_2026-06-07.md](examples/reports/IE00BK5BCD43_AIAI_MI_2026-06-07.md) |
| VanEck Semiconductor UCITS ETF (SMH.MI) | ETF | [IE00BMC38736_SMH_MI_2026-06-07.md](examples/reports/IE00BMC38736_SMH_MI_2026-06-07.md) |

## Acknowledgements

Extends CrewAI patterns from **Ed Donner's** Udemy course:

**[AI Engineer Agentic Track: The Complete Agent & MCP Course](https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/)**

Thank you to **Ed Donner** for the excellent agentic AI engineering course. Details in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

## Author

**Luca Amore** — [GitHub](https://github.com/lookee) · [lucaamore.com](https://www.lucaamore.com) · [LinkedIn](https://www.linkedin.com/in/lucaamore)

Free to use, copy, modify, and redistribute without restrictions.

## Disclaimer

**Experimental software** — coursework extension, not audited for production.

**No warranty** — provided *as is* without guarantees of correctness or fitness for purpose.

**Not financial advice** — reports are informational only; verify data against primary sources.

**Your responsibility** — API costs, third-party terms, and use of generated output.

## License

Public domain. See [LICENSE](LICENSE).
