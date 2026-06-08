# Financial Researcher

![Python](https://img.shields.io/badge/python-3.10--3.12-3776AB?logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-8957E5?logo=openai&logoColor=white)
![Status](https://img.shields.io/badge/status-experimental-red)

> One **executive briefing** for your whole **watchlist** — not one report per ticker.

A CLI that turns a list of ISINs into a single, cited strategy memo for **Borsa Italiana** instruments and **Milan trading sessions**. It pairs a deterministic data layer (Yahoo Finance + OpenFIGI) with a five-agent [CrewAI](https://crewai.com) workflow — four analysts in parallel, then a chief strategist who writes the memo.

📄 **[Sample briefing (English →)](examples/briefings/watchlist_2026-06-09_close.md)** · **[Italiano →](examples/briefings/watchlist_2026-06-09_close_it.md)** · ✍️ [Blog article](https://www.lucaamore.com/?p=2777)

---

## Why

- **Portfolio-level, not ticker-level** — cross-instrument narrative, leaders/laggards, shared themes.
- **Cited & verifiable** — every claim maps to a numbered Yahoo Finance or news source.
- **Milan-native** — four daily sessions aligned with Borsa Italiana hours.
- **Deterministic core** — prices and identities resolved in Python; agents reason, they don't invent data.

## Quickstart

```bash
pip install uv
uv sync
cp .env.sample .env        # add OPENAI_API_KEY and SERPER_API_KEY

uv run briefing            # session inferred from the Milan clock
```

The first run scaffolds `config/`, `output/briefings/`, and `data/`, and seeds `config/watchlist.yaml` from the example template.

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | ✅ | LLM backend for the agents |
| `SERPER_API_KEY` | ✅ | News and web search |
| `OPENFIGI_API_KEY` | — | Higher ISIN-resolution rate limits |
| `REPORT_LANGUAGE` | — | Override briefing language (e.g. `Italian`) |

## Usage

```bash
uv run briefing                              # auto session, default language
uv run briefing --session close              # explicit Milan session
uv run briefing --force --language Italian   # refresh cache + language
uv run briefing --watchlist path/to.yaml     # custom watchlist
```

| Flag | Description |
|------|-------------|
| `--session` | `pre_open` · `post_open` · `midday` · `close` (default: inferred from clock) |
| `--language LANG` | Briefing language (default: English) |
| `--force` | Refresh cached identity and market data |
| `--watchlist PATH` | Watchlist YAML path (default: `config/watchlist.yaml`) |

**Milan sessions** (Europe/Rome) — `pre_open` 08:45 · `post_open` 09:30 · `midday` 13:00 · `close` 17:45. When `--session` is omitted, the CLI picks the most recently passed slot ([schedule](src/financial_researcher/config/sessions_milan.yaml)).

```bash
# Cron: close briefing every weekday
45 17 * * 1-5 cd /path/to/financial_researcher && uv run briefing --session close
```

## Watchlist

Define instruments in `config/watchlist.yaml` — name, sector and category are resolved automatically.

```yaml
# language: Italian          # optional per-watchlist override
instruments:
  - { isin: IE00BK5BCD43, ticker: AIAI.MI,  type: etf }   # L&G AI
  - { isin: IE00BMC38736, ticker: SMH.MI,   type: etf }   # VanEck Semiconductors
  - { isin: IE00BP3QZ601, ticker: IWQU.MI,  type: etf }   # iShares World Quality
  - { isin: NL0000226223, ticker: STMMI.MI, type: stock } # STMicroelectronics
  - { isin: IT0003132476, ticker: ENI.MI,   type: stock } # Eni
  - { isin: NL0011585146, ticker: RACE.MI,  type: stock } # Ferrari
  - { isin: US0378331005, ticker: 1AAPL.MI, type: stock } # Apple (GEM)
```

| Field | Required | Description |
|-------|----------|-------------|
| `isin` | ✅ | 12-character ISIN |
| `ticker` | ✅ | Yahoo Finance ticker (e.g. `AIAI.MI`, `RACE.MI`, `1AAPL.MI`) |
| `type` | — | `stock` or `etf` — disambiguates ISIN resolution |

> The bundled [`config/watchlist.yaml.example`](config/watchlist.yaml.example) covers 3 ETFs + 4 Borsa Italiana equities (including Apple on the Global Equity Market), with no banking names.

## How it works

```
config/watchlist.yaml
   │  WatchlistPipeline ── OpenFIGI + Yahoo Finance  →  identities + snapshots ([1..N])
   ▼
CrewAI  ├─ market_analyst ─┐
        ├─ news_analyst    ├─ parallel analysts
        ├─ outlook_analyst │
        └─ calendar_analyst┘
                 ▼
        chief_strategist  →  output/briefings/watchlist_{DATE}_{SESSION}.md
```

1. **Resolve** every ISIN to an identity (OpenFIGI + Yahoo), cached locally.
2. **Fetch** market snapshots — prices, performance, ETF profile, forecasts (1-hour cache).
3. **Aggregate** context, performance table and theme map in Python.
4. **Run agents** — four analysts in parallel, then the chief strategist writes one cited memo.

| Agent | Role | Model | Tools |
|-------|------|-------|-------|
| `market_analyst` | Relative performance across the watchlist | gpt-4o-mini | Pre-loaded context |
| `news_analyst` | News & catalysts behind recent moves | gpt-4o | Serper · Yahoo news · scraping |
| `outlook_analyst` | 3–12 month macro & thematic outlook | gpt-4o-mini | Serper · scraping |
| `calendar_analyst` | Catalysts in the next 2–4 weeks | gpt-4o-mini | Serper · scraping |
| `chief_strategist` | Synthesises the final executive memo | gpt-4o | — |

Config: [`agents_briefing.yaml`](src/financial_researcher/config/agents_briefing.yaml) · [`tasks_briefing.yaml`](src/financial_researcher/config/tasks_briefing.yaml)

<details>
<summary><b>Briefing structure</b></summary>

Title block → Executive Summary → Performance Snapshot → What's Driving the Moves → Medium-Term Outlook → Event Calendar → Correlated Themes → Risks & Watchpoints → References → Disclaimer. Headings follow the configured language; citations are consolidated and numbered.
</details>

<details>
<summary><b>Output & caches</b></summary>

| Path | Description |
|------|-------------|
| `output/briefings/watchlist_{DATE}_{SESSION}.md` | Unified briefing (gitignored) |
| `data/identity/{ISIN}.json` | Cached instrument identity |
| `data/market/{ISIN}/latest.json` | Cached market snapshot (1 h TTL) |
</details>

<details>
<summary><b>Project structure</b></summary>

```
financial-researcher/
├── config/watchlist.yaml(.example)   # User watchlist + committed template
├── src/financial_researcher/
│   ├── main.py · crew.py · paths.py · settings.py
│   ├── config/    # agents, tasks, sessions, settings, fallback watchlist
│   ├── services/  # pipeline · context · isin_resolver · market_data
│   ├── storage/   # local JSON caches
│   └── tools/     # Serper news tools
├── examples/briefings/   # Sample output (tracked)
├── output/briefings/     # Generated briefings (gitignored)
└── data/                 # Runtime cache (gitignored)
```
</details>

<details>
<summary><b>Sample briefings</b></summary>

Generated from [`config/watchlist.yaml.example`](config/watchlist.yaml.example) (7 instruments):

| Language | Session | Briefing |
|----------|---------|----------|
| English | Close, 2026-06-09 | [watchlist_2026-06-09_close.md](examples/briefings/watchlist_2026-06-09_close.md) |
| Italian | Close, 2026-06-09 | [watchlist_2026-06-09_close_it.md](examples/briefings/watchlist_2026-06-09_close_it.md) |

Regenerate:

```bash
# English
uv run briefing --watchlist config/watchlist.yaml.example --session close --language English --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/

# Italian
uv run briefing --watchlist config/watchlist.yaml.example --session close --language Italian --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/watchlist_$(date +%Y-%m-%d)_close_it.md
```
</details>

## Acknowledgements

Extends CrewAI patterns from **Ed Donner's** [AI Engineer Agentic Track](https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/). Details in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

## Author

**Luca Amore** — [GitHub](https://github.com/lookee) · [lucaamore.com](https://www.lucaamore.com) · [LinkedIn](https://www.linkedin.com/in/lucaamore)

## Disclaimer

**Experimental** coursework extension — *as is*, no warranty. **Not financial advice**: briefings are informational only; verify against primary sources. You are responsible for API costs and third-party terms.

## License

Public domain. See [LICENSE](LICENSE).
