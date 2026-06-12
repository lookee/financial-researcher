# Financial Researcher

![Python](https://img.shields.io/badge/python-3.10--3.12-3776AB?logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-8957E5?logo=openai&logoColor=white)
![Status](https://img.shields.io/badge/status-experimental-red)

> One **executive briefing** for your whole **watchlist** — not one report per ticker.

Stop reading ten scattered ticker pages. **Financial Researcher** turns a plain list of ISINs into a single, board-ready strategy memo — the leaders, the laggards, the news that moved them, and what to watch next — every claim footnoted to a real source.

Under the hood, a deterministic Python data layer (Yahoo Finance + OpenFIGI) feeds a five-agent [CrewAI](https://crewai.com) newsroom: four analysts work the market, the news, the macro outlook and the event calendar **in parallel**, then a chief strategist writes the memo. It speaks **Borsa Italiana** and the **Milan trading clock** natively — the briefing reads differently at the open than at the close.

📄 **[Sample briefing (English →)](examples/briefings/watchlist_2026-06-10_close.md)** · ✍️ [Blog article](https://www.lucaamore.com/?p=2777)

---

## Why

- **Portfolio-level, not ticker-level** — one cross-instrument narrative with leaders, laggards and shared themes, instead of N disconnected reports.
- **Cited & verifiable** — every figure and claim maps to a numbered Yahoo Finance or news source. No anonymous assertions.
- **Milan-native** — four daily sessions aligned with Borsa Italiana hours; the memo's tone and metrics adapt to the time of day.
- **Deterministic core** — prices and identities are resolved in Python and cached; the agents reason over real data, they don't invent it.
- **Bilingual** — generate the same briefing in English or Italian from one watchlist.

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
| `FINNHUB_API_KEY` | — | Company news prefetch (merged with Yahoo/Serper) |
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

### The four moments of the Milan day

The briefing is **session-aware**: the same watchlist produces a different memo depending on where you are in the Borsa Italiana day (Europe/Rome). When `--session` is omitted, the CLI picks the most recently passed slot ([schedule](src/financial_researcher/config/sessions_milan.yaml)).

| Session | Clock | The memo's job | What it leans on |
|---------|-------|----------------|------------------|
| `pre_open` | **08:45** | *What does today face?* Forward-looking — no intraday recap yet | Previous close, index futures, overnight moves (Asia close, US futures), scheduled catalysts |
| `post_open` | **09:30** | *How did we open?* The reaction in the first minutes | The **gap** vs previous close and the news driving it (prices still thin/noisy) |
| `midday` | **13:00** | *Where do we stand at lunch?* Session in progress | **Partial** intraday move, the morning's headlines, what the afternoon still holds |
| `close` | **17:45** | *How did the day end — and what's next?* Full recap + setup | Final 1D/1W/1M/YTD, the day's drivers, the next 2–4 weeks of catalysts |

```bash
# Morning preview, then evening wrap-up
uv run briefing --session pre_open
uv run briefing --session close
```

## Watchlist

Define instruments in `config/watchlist.yaml` — name, sector and category are resolved automatically.

```yaml
# language: Italian          # optional per-watchlist override
instruments:
  - { isin: IE00BMC38736, ticker: SMH.MI,   type: etf }   # VanEck Semiconductors
  - { isin: IE00BDVPNG13, ticker: WTAI.MI,  type: etf }   # WisdomTree AI
  - { isin: US67066G1040, ticker: 1NVDA.MI, type: stock } # NVIDIA (GEM)
  - { isin: NL0000226223, ticker: STMMI.MI, type: stock } # STMicroelectronics
```

| Field | Required | Description |
|-------|----------|-------------|
| `isin` | ✅ | 12-character ISIN |
| `ticker` | ✅ | Yahoo Finance ticker (e.g. `SMH.MI`, `STMMI.MI`, `1NVDA.MI`) |
| `type` | — | `stock` or `etf` — disambiguates ISIN resolution |

> The bundled [`config/watchlist.yaml.example`](config/watchlist.yaml.example) is an **AI & hypertech** theme on Borsa Italiana: 2 thematic ETFs (semiconductors + AI) plus 2 AI bellwether stocks, including NVIDIA on the Global Equity Market (GEM).

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
| `market_analyst` | Relative performance across the watchlist | gpt-5.5 | Pre-loaded context |
| `news_analyst` | News & catalysts behind recent moves | gpt-5.5 | Serper · Yahoo news · scraping |
| `outlook_analyst` | 3–12 month macro & thematic outlook | gpt-5.5 | Serper · scraping |
| `calendar_analyst` | Catalysts in the next 2–4 weeks | gpt-5.4-mini | Serper · scraping |
| `chief_strategist` | Synthesises the final executive memo | gpt-5.5 | — |

Config: [`agents_briefing.yaml`](src/financial_researcher/config/agents_briefing.yaml) · [`tasks_briefing.yaml`](src/financial_researcher/config/tasks_briefing.yaml)

> [!WARNING]
> **This default lineup is tuned for quality, not for your wallet.** Four of the five agents run on the **most capable — and most expensive — frontier model** (`gpt-5.5`). A single full briefing makes many LLM calls plus news search and page scraping, so cost adds up quickly when you run it several times a day.
>
> **Want to pay less?** Downgrade the models in [`agents_briefing.yaml`](src/financial_researcher/config/agents_briefing.yaml) — change the `llm:` line of any agent to a cheaper tier (e.g. `openai/gpt-5.4-mini`, or an even smaller/older model like `openai/gpt-4o-mini`). The briefing will still generate; expect a **less nuanced narrative and weaker synthesis** in exchange for materially lower cost. The `chief_strategist` and `news_analyst` benefit most from a strong model — downgrade the others first if you want a balance.

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

Generated from [`config/watchlist.yaml.example`](config/watchlist.yaml.example) (4 instruments — AI & hypertech theme):

| Language | Session | Briefing |
|----------|---------|----------|
| English | Close, 2026-06-10 | [watchlist_2026-06-10_close.md](examples/briefings/watchlist_2026-06-10_close.md) |

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
