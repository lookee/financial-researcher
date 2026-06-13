# Financial Researcher

![Python](https://img.shields.io/badge/python-3.10--3.12-3776AB?logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-8957E5?logo=openai&logoColor=white)
![CI](https://github.com/lookee/financial-researcher/actions/workflows/ci.yml/badge.svg)
![Status](https://img.shields.io/badge/status-experimental-red)

> One **executive briefing** for your whole **watchlist** — not one report per ticker.

Stop reading ten scattered ticker pages. **Financial Researcher** turns a plain list of ISINs into a single, board-ready strategy memo — the leaders, the laggards, the news that moved them, and what to watch next — every claim footnoted to a real source.

Under the hood, a deterministic Python data layer (Yahoo Finance + OpenFIGI) feeds a five-agent [CrewAI](https://crewai.com) newsroom: four analysts work the market, the news, the macro outlook and the event calendar **in parallel**, then a chief strategist writes the memo. It speaks **Borsa Italiana** and the **Milan trading clock** natively — the briefing reads differently at the open than at the close.

## Sample briefings

Static samples live in [`examples/briefings/`](examples/briefings/) (tracked in git). Each file is one full executive memo; language and Milan session are listed below.

| Language | Date | Session | Briefing |
|----------|------|---------|----------|
| Italian | 2026-06-09 | `close` | [watchlist_2026-06-09_close.md](examples/briefings/watchlist_2026-06-09_close.md) |
| Italian | 2026-06-10 | `close` | [watchlist_2026-06-10_close.md](examples/briefings/watchlist_2026-06-10_close.md) |
| Italian | 2026-06-11 | `close` | [watchlist_2026-06-11_close.md](examples/briefings/watchlist_2026-06-11_close.md) |
| Italian | 2026-06-12 | `post_open` | [watchlist_2026-06-12_post_open.md](examples/briefings/watchlist_2026-06-12_post_open.md) |
| Italian | 2026-06-12 | `midday` | [watchlist_2026-06-12_midday.md](examples/briefings/watchlist_2026-06-12_midday.md) |
| Italian | 2026-06-12 | `close` | [watchlist_2026-06-12_close.md](examples/briefings/watchlist_2026-06-12_close.md) |
| English | 2026-06-12 | `close` | [watchlist_2026-06-12_close_en.md](examples/briefings/watchlist_2026-06-12_close_en.md) |

Italian samples were generated from a 6-instrument personal watchlist (not the 4-instrument [`config/watchlist.yaml.example`](config/watchlist.yaml.example)). To add an English sample or refresh an existing file:

```bash
# English — example watchlist
uv run briefing --watchlist config/watchlist.yaml.example --session close --language English --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/

# Italian
uv run briefing --watchlist config/watchlist.yaml.example --session close --language Italian --force
cp output/briefings/watchlist_$(date +%Y-%m-%d)_close.md examples/briefings/watchlist_$(date +%Y-%m-%d)_close.md
```

New runs are written to `output/briefings/` (gitignored) unless you copy them into `examples/briefings/` as above.

✍️ [Blog article](https://www.lucaamore.com/?p=2777)

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

Use `uv run briefing` directly — avoid activating another project's `.venv` first, or `uv` may warn about a mismatched `VIRTUAL_ENV`. CrewAI agent/task progress is shown by default; add `--quiet` (or `BRIEFING_QUIET=1`) to hide it.

The first run scaffolds `./config/` (your watchlist), `output/briefings/`, and `data/`, and seeds `config/watchlist.yaml` from the example template.

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | ✅* | LLM for `balanced`, `frontier`, `budget`, `multi` profiles |
| `ANTHROPIC_API_KEY` | — | Required for `anthropic` or `multi` |
| `DEEPSEEK_API_KEY` | — | Required for `deepseek` or `multi` |
| `SERPER_API_KEY` | ✅ | News and web search |
| `SERPER_FREE_TIER` | — | Set `0` if you have a paid Serper plan (keeps `site:` queries) |
| `FINNHUB_API_KEY` | — | Optional Finnhub company-news prefetch (merged with Yahoo/Serper) |
| `FINNHUB_ENABLED` | — | Set `false` to disable Finnhub even when a key is set (default: `true`) |
| `FINNHUB_NEWS_LOOKBACK_DAYS` | — | Days of Finnhub news history per instrument (default: `14`, max `30`) |
| `OPENFIGI_API_KEY` | — | Higher ISIN-resolution rate limits |
| `REPORT_LANGUAGE` | — | Override briefing language (e.g. `Italian`) |
| `FR_MODEL_PROFILE` | — | Model lineup — see [Model profiles](#model-profiles) and [`model_profiles.yaml`](src/financial_researcher/defaults/model_profiles.yaml) |
| `GROQ_API_KEY` | — | Required for `--model-profile free_groq` (no OpenAI key needed) |
| `OPENROUTER_API_KEY` | — | Required for `--model-profile free_openrouter_nex` (no OpenAI key needed) |
| `FR_MODEL_*` | — | Per-agent model override (e.g. `FR_MODEL_CHIEF`) — beats the active profile |
| `WATCHLIST_PATH` | — | Override watchlist YAML location (default: `./config/watchlist.yaml`) |
| `FINANCIAL_RESEARCHER_CONFIG_DIR` | — | Global user config directory (default: `~/.config/financial_researcher`) |
| `FINANCIAL_RESEARCHER_HOME` | — | Base directory for `output/` and `data/` (default: current working directory) |
| `BRIEFING_QUIET` | — | Set `1` to hide CrewAI agent/task progress (same as `--quiet`) |

\*Not required for single-provider profiles that use another backend (`anthropic`, `deepseek`, `free_groq`, `free_openrouter_nex`). The `multi` profile needs OpenAI + Anthropic + DeepSeek.

## Usage

```bash
uv run briefing                              # auto session, default language
uv run briefing --session close              # explicit Milan session
uv run briefing --force --language Italian   # refresh cache + language
uv run briefing --model-profile frontier     # all gpt-5.5 lineup
uv run briefing --watchlist path/to.yaml     # custom watchlist
```

| Flag | Description |
|------|-------------|
| `--session` | `pre_open` · `post_open` · `midday` · `close` (default: inferred from clock) |
| `--language LANG` | Briefing language (default: English) |
| `--force` | Refresh cached identity and market data |
| `--watchlist PATH` | Watchlist YAML path (default: `config/watchlist.yaml`) |
| `--model-profile` | See [Model profiles](#model-profiles) (default: `balanced`) |
| `--quiet` | Hide CrewAI agent/task progress (default: shown) |

## Configuration

Two directories — different roles:

| Path | Role |
|------|------|
| **`./config/`** | Your data: `watchlist.yaml` ([`config/README.md`](config/README.md)) |
| **`src/financial_researcher/defaults/`** | Shipped app defaults: agents, tasks, settings, model profiles, Milan sessions |

Application defaults live in `src/financial_researcher/defaults/settings.yaml` (language, scrape behaviour, model profiles, etc.). Your watchlist lives in `./config/watchlist.yaml`. `REPORT_LANGUAGE` in `.env` overrides `default_language`.

### Website scrape truncation

News, outlook and calendar agents use `ScrapeWebsiteTool` for institutional pages. By default, scraped text is **truncated to 2,500 characters** before it reaches the LLM: paragraphs matching the instrument name/ticker or query keywords are kept first; otherwise the start of the page is used. Trimmed output ends with `[...troncato]`.

```yaml
# src/financial_researcher/defaults/settings.yaml
serper:
  free_tier: true   # simplify site:/OR queries for Serper free plans (default)

scrape:
  truncate_enabled: true   # set false for full page text (higher token use)
  max_chars: 2500
```

### Determinism & post-processing

Several briefing guarantees are enforced in Python rather than in agent prompts:

- **1D consistency** — canonical daily change from quote fields; `⚠` when quote and history diverge
- **Material news** — prefetch emits `Impact **NONE**` instead of promoting ETF/profile pages as headlines
- **Post-process** — cap on `🔴` tags, continuous research citation numbering, calendar table column normalisation
- **Performance table** — injected by the pipeline (price column, one `[N]` per row)
- **News agent** — prefetch-first workflow with a hard cap on gap-filling tool calls (4 per instrument, 12 per run)
- **Finnhub prefetch** — when `FINNHUB_API_KEY` is set and `FINNHUB_ENABLED` is not disabled, company news is fetched per stock and merged into the deterministic prefetch layer alongside Yahoo and Serper headlines

After each run, token usage and post-process warnings are written to `output/metrics/run_{date}_{session}.json`, and a one-line summary is printed:

```text
Tokens: prompt=… completion=… | requests=… | warnings=…
```

## Usage details

### The four moments of the Milan day

The briefing is **session-aware**: the same watchlist produces a different memo depending on where you are in the Borsa Italiana day (Europe/Rome). When `--session` is omitted, the CLI picks the most recently passed slot ([schedule](src/financial_researcher/defaults/sessions_milan.yaml)).

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

| Agent | Role | Model (`balanced`) | Tools |
|-------|------|-------|-------|
| `market_analyst` | Relative performance across the watchlist | gpt-5.4-mini | Pre-loaded context |
| `news_analyst` | News & catalysts behind recent moves | gpt-5.5 | Serper · Yahoo news · scraping |
| `outlook_analyst` | 3–12 month macro & thematic outlook | gpt-5.4 | Serper · scraping |
| `calendar_analyst` | Catalysts in the next 2–4 weeks | gpt-5.4-mini | Serper · scraping |
| `chief_strategist` | Synthesises the final executive memo | gpt-5.5 | — |

Config: [`agents_briefing.yaml`](src/financial_researcher/defaults/agents_briefing.yaml) · [`tasks_briefing.yaml`](src/financial_researcher/defaults/tasks_briefing.yaml) · [`model_profiles.yaml`](src/financial_researcher/defaults/model_profiles.yaml) · [`agent_llm.py`](src/financial_researcher/agent_llm.py)

### Model profiles

Agents route through [LiteLLM](https://docs.litellm.ai/docs/providers) (via CrewAI). The briefing pipeline works with **OpenAI**, **Anthropic**, **DeepSeek**, **Groq**, and **OpenRouter** — pick a profile or override individual agents with `FR_MODEL_*`.

| Profile | API keys needed | Lineup (summary) |
|---------|-----------------|------------------|
| `balanced` | `OPENAI_API_KEY` | **Default** — mini on market/calendar, `gpt-5.4` outlook, `gpt-5.5` news + chief |
| `frontier` | `OPENAI_API_KEY` | all `gpt-5.5`, higher reasoning on news/chief |
| `budget` | `OPENAI_API_KEY` | mini on all analysts, `gpt-5.4` chief |
| `anthropic` | `ANTHROPIC_API_KEY` | Haiku on market/calendar, Sonnet 4.6 on news/chief |
| `deepseek` | `DEEPSEEK_API_KEY` | V4 Flash on analysts, V4 Pro on news/chief |
| `multi` | OpenAI + Anthropic + DeepSeek | Flash analysts · Sonnet news · `gpt-5.4` outlook · `gpt-5.5` chief |
| `free_groq` | `GROQ_API_KEY` | Llama via Groq — experimental |
| `free_openrouter_nex` | `OPENROUTER_API_KEY` | [Nex-N2-Pro (free)](https://openrouter.ai/nex-agi/nex-n2-pro:free) — experimental |

```bash
uv run briefing --model-profile deepseek               # DeepSeek only
uv run briefing --model-profile multi                  # OpenAI + Anthropic + DeepSeek
uv run briefing --model-profile anthropic              # Claude Haiku + Sonnet 4.6
uv run briefing --model-profile free_openrouter_nex
uv run briefing --model-profile budget
export FR_MODEL_PROFILE=frontier
```

Set `model_profile: budget` in `defaults/settings.yaml` for a persistent default. Per-agent `FR_MODEL_*` env vars still override one slot in the active profile.

> [!NOTE]
> **Provider notes**
> - **`deepseek`** — [DeepSeek V4](https://api-docs.deepseek.com/) via `deepseek/deepseek-v4-flash` and `deepseek/deepseek-v4-pro`. Set `DEEPSEEK_API_KEY` only.
> - **`multi`** — assigns each provider where it fits best: cheap DeepSeek for table analysts, Anthropic for news synthesis, OpenAI for outlook + final memo. All three API keys required.
> - **`anthropic`** — [Claude Haiku 4.5](https://www.anthropic.com/news/claude-haiku-4-5) + [Sonnet 4.6](https://docs.litellm.ai/docs/providers/anthropic).
> - **`free_*`** — experimental; weaker citations than `balanced`.

> [!WARNING]
> **Default profile (`balanced`) targets cost vs quality.** Analyst agents emit terse internal handoffs; reasoning effort is tuned per agent — together this typically cuts completion tokens by roughly half versus `frontier`. A full run still makes many LLM calls plus news search and page scraping.
>
> **Want all-frontier quality?** Use `--model-profile frontier` or per-agent overrides (see `.env.sample`).

**Prompt caching:** agent role/goal/backstory in `agents_briefing.yaml` are static (no dates or session placeholders). Run-specific tables and dates are appended at the end of each task description under `--- RUN CONTEXT ---`, so OpenAI can cache the shared instruction prefix across runs.

<details>
<summary><b>Briefing structure</b></summary>

Title block → Executive Summary → Performance Snapshot → What's Driving the Moves → Medium-Term Outlook → Event Calendar → Correlated Themes → Risks & Watchpoints → References → Disclaimer. Headings follow the configured language; citations are consolidated and numbered.
</details>

<details>
<summary><b>Output & caches</b></summary>

| Path | Description |
|------|-------------|
| `output/briefings/watchlist_{DATE}_{SESSION}.md` | Unified briefing (gitignored) |
| `output/metrics/run_{DATE}_{SESSION}.json` | Token usage and post-process warnings per run (gitignored) |
| `data/identity/{ISIN}.json` | Cached instrument identity |
| `data/market/{ISIN}/latest.json` | Cached market snapshot (1 h TTL) |
</details>

<details>
<summary><b>Project structure</b></summary>

```
financial-researcher/
├── config/                 # Your watchlist (watchlist.yaml; see config/README.md)
├── src/financial_researcher/
│   ├── main.py · crew.py · paths.py · settings.py · llm_compat.py · session_profiles.py
│   ├── defaults/           # Shipped app config: agents, tasks, settings, model profiles
│   ├── models/    # instrument identity types
│   ├── services/  # pipeline · context · isin_resolver · market_data · news_prefetch
│   │              # news_ranking · briefing_postprocess · run_metrics
│   │              # news_providers/ (Finnhub + merge)
│   ├── storage/   # local JSON caches
│   └── tools/     # Serper news/search tools · limited scrape
├── tests/                # pytest suite
├── examples/briefings/   # Sample output (tracked)
├── output/briefings/     # Generated briefings (gitignored)
├── output/metrics/       # Per-run token/warning JSON (gitignored)
└── data/                 # Runtime cache (gitignored)
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
