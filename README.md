# Financial Researcher

![Python](https://img.shields.io/badge/python-3.10--3.12-3776AB?logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-8957E5?logo=openai&logoColor=white)
![Status](https://img.shields.io/badge/status-experimental-red)

CLI tool that generates a **single executive briefing** for your entire **watchlist** — not one report per instrument. Output reads like a senior strategy consultant memo, with cited market data and news, focused on **Borsa Italiana** instruments and **Milan trading sessions**.

Built with a deterministic data layer and a five-agent [CrewAI](https://crewai.com) workflow (four parallel analysts + chief strategist).

[Article from my blog](https://www.lucaamore.com/?p=2777)

## Requirements

| Requirement | Details |
|-------------|---------|
| Python | 3.10 – 3.12 |
| Package manager | [uv](https://github.com/astral-sh/uv) (recommended) |
| API keys | `OPENAI_API_KEY`, `SERPER_API_KEY` — see [Setup](#setup) |

## Setup

```bash
pip install uv
uv sync
cp .env.sample .env
```

Edit `.env` and set your API keys:

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | LLM backend for CrewAI agents |
| `SERPER_API_KEY` | Yes | News and web search tools |
| `OPENFIGI_API_KEY` | No | Higher OpenFIGI rate limits for ISIN resolution |
| `REPORT_LANGUAGE` | No | Override briefing language (e.g. `Italian`) |

On first run the CLI creates `output/briefings/`, `data/identity/`, `data/market/`, and `config/` automatically.

Copy `config/watchlist.yaml.example` to `config/watchlist.yaml` (or let the CLI create it on first run) and edit your instruments there.

## Usage

### Generate a briefing

```bash
# Infer Milan session from current Europe/Rome time
uv run briefing

# Explicit session
uv run briefing --session close

# Refresh cached data and set language
uv run briefing --force --language Italian

# Custom watchlist file
uv run briefing --watchlist path/to/watchlist.yaml
```

### Options

| Flag | Description |
|------|-------------|
| `--session` | Milan session: `pre_open`, `post_open`, `midday`, `close` (default: inferred from clock) |
| `--force` | Refresh cached identity and market data |
| `--language LANG` | Briefing language (default: English from settings) |
| `--watchlist PATH` | Watchlist YAML path (default: `config/watchlist.yaml` in the project directory) |

### Milan sessions (Europe/Rome)

Four sessions per trading day, aligned with Borsa Italiana:

| Session | Time | When to use |
|---------|------|-------------|
| `pre_open` | 08:45 | Before the opening auction |
| `post_open` | 09:30 | After the market opens |
| `midday` | 13:00 | Mid-session check |
| `close` | 17:45 | End-of-day wrap-up |

Schedule config: [`sessions_milan.yaml`](src/financial_researcher/config/sessions_milan.yaml)

When `--session` is omitted, the CLI picks the session whose scheduled time most recently passed.

Example cron (close briefing, weekdays):

```bash
45 17 * * 1-5 cd /path/to/financial_researcher && uv run briefing --session close
```

## Watchlist

Instruments are defined in `config/watchlist.yaml` (user config, not in source code):

```yaml
# Optional: override default_language for this watchlist only
# language: Italian

instruments:
  - isin: IE00BK5BCD43
    ticker: AIAI.MI
    type: etf

  - isin: US67066G1040
    ticker: NVDA
    type: stock
```

| Field | Required | Description |
|-------|----------|-------------|
| `isin` | Yes | 12-character ISIN |
| `ticker` | Yes | Yahoo Finance ticker (e.g. `AIAI.MI`, `ISP.MI`, `NVDA`) |
| `type` | No | `stock` or `etf` — helps ISIN resolution when OpenFIGI is ambiguous |

Name, sector and category are resolved automatically from OpenFIGI and Yahoo Finance.

Default watchlist: **AIAI.MI**, **SMH.MI**, **SWDA.MI** (Milan-listed UCITS ETFs).

## Briefing language

Default: **English**.

Configure globally in [`settings.yaml`](src/financial_researcher/config/settings.yaml) (`default_language`) or via `.env` (`REPORT_LANGUAGE=Italian`). Per-run override: `--language Italian`.

---

## How it works

### Overview

1. **Resolve** each watchlist instrument from ISIN via OpenFIGI and Yahoo Finance; cache identity locally.
2. **Fetch** market snapshots — prices, performance, ETF profile, stock forecasts — with a 1-hour cache.
3. **Aggregate** watchlist context, performance table, and theme map in Python (`watchlist_context`).
4. **Run agents** — four analysts **in parallel** (market, news, outlook, calendar), then chief strategist — to produce one cited executive memo.

> **Note:** Experimental software for learning and exploration, not production use. See [Disclaimer](#disclaimer).

### Pipeline

```
config/watchlist.yaml
    │
    ├─ WatchlistPipeline       ISIN resolve + Yahoo Finance snapshots
    └─ watchlist_context       JSON + market_pulse_table + profiles  →  [1..N]
            │
            ▼
    CrewAI (sequential process, parallel async tasks)
    ├─ market_analyst   ─┐
    ├─ news_analyst     ─┤
    ├─ outlook_analyst  ─┼─ parallel (async_execution)
    └─ calendar_analyst ─┘
            │
            ▼
    chief_strategist (gpt-4o)   unified executive briefing memo
            │
            ▼
    output/briefings/watchlist_{DATE}_{SESSION}.md
```

### Briefing structure

The final memo includes (headings in the configured language):

1. Title block — session, date, time, market
2. **Executive Summary** — prioritised cross-instrument narrative
3. Watchlist Performance Snapshot
4. What's Driving the Moves
5. Medium-Term Outlook — themes, scenarios, macro
6. Event Calendar — upcoming 2–4 week catalysts
7. Correlated Themes — macro, sector, Milan/Europe links
8. Risks & Watchpoints
9. References — consolidated numbered citations
10. Disclaimer

### Agents

Research analysts use **GPT-4o mini**; the chief strategist uses **GPT-4o** (configurable in YAML).

#### `market_analyst`

| | |
|---|---|
| **Purpose** | Analyse relative performance across the watchlist |
| **Tools** | None — uses pre-loaded `watchlist_context` and `market_pulse_table` |
| **Citations** | One Yahoo Finance reference per instrument (`[1]`..`[N]`) |

#### `news_analyst`

| | |
|---|---|
| **Purpose** | Find news and catalysts explaining recent moves (24–48 h) |
| **Tools** | [Serper](https://serper.dev) search & news, Yahoo Finance news, website scraping |
| **Citations** | New sources from **`[N+1]`** onward |

#### `outlook_analyst`

| | |
|---|---|
| **Purpose** | Medium-term (3–12 month) macro and thematic outlook |
| **Tools** | Serper search & news, website scraping |
| **Focus** | ECB/Fed, sector cycles, bull/base/bear scenarios per theme |

#### `calendar_analyst`

| | |
|---|---|
| **Purpose** | Upcoming events in the next 2–4 weeks |
| **Tools** | Serper search & news, website scraping |
| **Focus** | Central banks, macro prints, theme-proxy earnings |

#### `chief_strategist`

| | |
|---|---|
| **Purpose** | Write the final executive briefing |
| **Tools** | None — synthesises all four analyst outputs |
| **LLM** | GPT-4o — stronger synthesis and prose |
| **Style** | Senior strategy consultant memo; no buy/sell/hold advice |

Agent and task configuration:

- [`agents_briefing.yaml`](src/financial_researcher/config/agents_briefing.yaml)
- [`tasks_briefing.yaml`](src/financial_researcher/config/tasks_briefing.yaml)

## Output

| Path | Description |
|------|-------------|
| `output/briefings/watchlist_{DATE}_{SESSION}.md` | Unified executive briefing (local, gitignored) |
| `data/identity/{ISIN}.json` | Cached instrument identity |
| `data/market/{ISIN}/latest.json` | Cached market snapshot (1 h TTL) |

Example filename: `output/briefings/watchlist_2026-06-07_close.md`

## Project structure

```
financial-researcher/
├── config/
│   ├── watchlist.yaml.example  # Template (committed)
│   └── watchlist.yaml          # Your instruments (gitignored)
├── src/financial_researcher/
│   ├── main.py                 # CLI entry point (briefing)
│   ├── crew.py                 # WatchlistBriefingCrew
│   ├── paths.py                # User config path resolution
│   ├── settings.py             # Language and config loader
│   ├── config/
│   │   ├── watchlist.example.yaml  # Fallback template for first-run init
│   │   ├── sessions_milan.yaml # Milan session times
│   │   ├── settings.yaml       # Default language
│   │   ├── agents_briefing.yaml
│   │   └── tasks_briefing.yaml
│   ├── services/
│   │   ├── watchlist_pipeline.py   # Resolve + fetch batch
│   │   ├── watchlist_context.py    # Crew inputs builder
│   │   ├── isin_resolver.py        # OpenFIGI + Yahoo identity
│   │   └── market_data.py          # Yahoo Finance snapshots
│   ├── storage/                # Local JSON caches
│   └── tools/                  # Serper news tool
├── examples/briefings/         # Sample output (tracked in git)
├── output/briefings/           # Generated briefings (gitignored)
└── data/                       # Runtime cache (gitignored)
```

## Sample briefing

Static example in [`examples/briefings/`](examples/briefings/):

| Session | Briefing |
|---------|----------|
| Close, 2026-06-07 | [watchlist_2026-06-07_close.md](examples/briefings/watchlist_2026-06-07_close.md) |

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

**Not financial advice** — briefings are informational only; verify data against primary sources.

**Your responsibility** — API costs, third-party terms, and use of generated output.

## License

Public domain. See [LICENSE](LICENSE).
