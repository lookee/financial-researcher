# Financial Researcher

[![Python](https://img.shields.io/badge/python-3.10--3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/lookee/financial_researcher/main/.github/badges/tests.json&query=$.message&label=tests&color=brightgreen&logo=pytest&logoColor=white&cacheSeconds=600)](tests/)
[![CI](https://github.com/lookee/financial-researcher/actions/workflows/ci.yml/badge.svg)](https://github.com/lookee/financial-researcher/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Unlicense-blue)](LICENSE)
[![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-8957E5?logo=openai&logoColor=white)](https://crewai.com)
[![LLM](https://img.shields.io/badge/LLM-OpenAI%20%7C%20Anthropic%20%7C%20DeepSeek%20%7C%20OpenRouter-8957E5)](src/financial_researcher/defaults/model_profiles.yaml)
[![Market](https://img.shields.io/badge/market-Borsa%20Italiana%20(Milan)-006E48)](src/financial_researcher/defaults/sessions_milan.yaml)
[![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Status](https://img.shields.io/badge/status-experimental-red)](#)

> One **executive briefing** for your whole **watchlist** — not one report per ticker.

Stop reading ten scattered ticker pages. **Financial Researcher** turns a plain list of ISINs into a single, board-ready strategy memo — the leaders, the laggards, the news that moved them, and what to watch next — every claim footnoted to a real source.

Under the hood, a deterministic Python data layer (Yahoo Finance + OpenFIGI) feeds a five-agent [CrewAI](https://crewai.com) newsroom: four analysts work the market, the news, the macro outlook and the event calendar **in parallel**, then a chief strategist writes the memo. It speaks **Borsa Italiana** and the **Milan trading clock** natively — the briefing reads differently at the open than at the close.

## Sample briefings

Static samples live in [`examples/briefings/`](examples/briefings/) (tracked in git). Each file is one full executive memo; **body** language and Milan session are listed below (newest first). Section headings in all samples are **English**. Session charts are in [`examples/briefings/charts/`](examples/briefings/charts/).

| Body | Date | Session | Briefing |
|------|------|---------|----------|
| Italian | 2026-06-24 | `close` | [watchlist_2026-06-24_close.md](examples/briefings/watchlist_2026-06-24_close.md) |
| Italian | 2026-06-24 | `midday` | [watchlist_2026-06-24_midday.md](examples/briefings/watchlist_2026-06-24_midday.md) |
| Italian | 2026-06-24 | `pre_open` | [watchlist_2026-06-24_pre_open.md](examples/briefings/watchlist_2026-06-24_pre_open.md) |
| Italian | 2026-06-23 | `close` | [watchlist_2026-06-23_close.md](examples/briefings/watchlist_2026-06-23_close.md) |
| Italian | 2026-06-23 | `midday` | [watchlist_2026-06-23_midday.md](examples/briefings/watchlist_2026-06-23_midday.md) |
| Italian | 2026-06-23 | `post_open` | [watchlist_2026-06-23_post_open.md](examples/briefings/watchlist_2026-06-23_post_open.md) |
| Italian | 2026-06-23 | `pre_open` | [watchlist_2026-06-23_pre_open.md](examples/briefings/watchlist_2026-06-23_pre_open.md) |
| Italian | 2026-06-22 | `close` | [watchlist_2026-06-22_close.md](examples/briefings/watchlist_2026-06-22_close.md) |
| Italian | 2026-06-22 | `midday` | [watchlist_2026-06-22_midday.md](examples/briefings/watchlist_2026-06-22_midday.md) |
| Italian | 2026-06-19 | `close` | [watchlist_2026-06-19_close.md](examples/briefings/watchlist_2026-06-19_close.md) |
| Italian | 2026-06-19 | `pre_open` | [watchlist_2026-06-19_pre_open.md](examples/briefings/watchlist_2026-06-19_pre_open.md) |
| Italian | 2026-06-18 | `close` | [watchlist_2026-06-18_close.md](examples/briefings/watchlist_2026-06-18_close.md) |
| Italian | 2026-06-18 | `midday` | [watchlist_2026-06-18_midday.md](examples/briefings/watchlist_2026-06-18_midday.md) |
| Italian | 2026-06-18 | `post_open` | [watchlist_2026-06-18_post_open.md](examples/briefings/watchlist_2026-06-18_post_open.md) |
| Italian | 2026-06-18 | `pre_open` | [watchlist_2026-06-18_pre_open.md](examples/briefings/watchlist_2026-06-18_pre_open.md) |
| Italian | 2026-06-17 | `close` | [watchlist_2026-06-17_close.md](examples/briefings/watchlist_2026-06-17_close.md) |
| Italian | 2026-06-17 | `midday` | [watchlist_2026-06-17_midday.md](examples/briefings/watchlist_2026-06-17_midday.md) |
| Italian | 2026-06-17 | `post_open` | [watchlist_2026-06-17_post_open.md](examples/briefings/watchlist_2026-06-17_post_open.md) |
| Italian | 2026-06-16 | `close` | [watchlist_2026-06-16_close.md](examples/briefings/watchlist_2026-06-16_close.md) |
| Italian | 2026-06-16 | `post_open` | [watchlist_2026-06-16_post_open.md](examples/briefings/watchlist_2026-06-16_post_open.md) |
| Italian | 2026-06-15 | `close` | [watchlist_2026-06-15_close.md](examples/briefings/watchlist_2026-06-15_close.md) |
| Italian | 2026-06-15 | `post_open` | [watchlist_2026-06-15_post_open.md](examples/briefings/watchlist_2026-06-15_post_open.md) |
| Italian | 2026-06-15 | `pre_open` | [watchlist_2026-06-15_pre_open.md](examples/briefings/watchlist_2026-06-15_pre_open.md) |
| Italian | 2026-06-13 | `close` | [watchlist_2026-06-13_close.md](examples/briefings/watchlist_2026-06-13_close.md) |
| Italian | 2026-06-12 | `close` | [watchlist_2026-06-12_close.md](examples/briefings/watchlist_2026-06-12_close.md) |
| English | 2026-06-12 | `close` | [watchlist_2026-06-12_close_en.md](examples/briefings/watchlist_2026-06-12_close_en.md) |
| Italian | 2026-06-12 | `midday` | [watchlist_2026-06-12_midday.md](examples/briefings/watchlist_2026-06-12_midday.md) |
| Italian | 2026-06-12 | `post_open` | [watchlist_2026-06-12_post_open.md](examples/briefings/watchlist_2026-06-12_post_open.md) |
| Italian | 2026-06-11 | `close` | [watchlist_2026-06-11_close.md](examples/briefings/watchlist_2026-06-11_close.md) |
| Italian | 2026-06-10 | `close` | [watchlist_2026-06-10_close.md](examples/briefings/watchlist_2026-06-10_close.md) |
| Italian | 2026-06-09 | `close` | [watchlist_2026-06-09_close.md](examples/briefings/watchlist_2026-06-09_close.md) |


✍️ [Blog article](https://www.lucaamore.com/?p=2777)

---

## Why

- **Portfolio-level, not ticker-level** — one cross-instrument narrative with leaders, laggards and shared themes, instead of N disconnected reports.
- **Cited & verifiable** — every figure and claim maps to a numbered Yahoo Finance or news source. No anonymous assertions.
- **Milan-native** — four daily sessions aligned with Borsa Italiana hours; the memo's tone and metrics adapt to the time of day.
- **Deterministic core** — prices and identities are resolved in Python and cached; the agents reason over real data, they don't invent it.
- **English structure** — section titles, run-metadata labels and chart headings are always English ([`localization.py`](src/financial_researcher/localization.py)); `--language` / `REPORT_LANGUAGE` controls briefing **prose** and table formatting (English or Italian).

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
| `OPENAI_API_KEY` | ✅* | LLM for `openai_*` and `mixed_balanced` profiles |
| `ANTHROPIC_API_KEY` | — | Required for `anthropic_balanced` or `mixed_balanced` |
| `DEEPSEEK_API_KEY` | — | Required for `deepseek_balanced` or `mixed_balanced` |
| `SERPER_API_KEY` | ✅ | News and web search |
| `SERPER_FREE_TIER` | — | Set `0` if you have a paid Serper plan (keeps `site:` queries) |
| `FINNHUB_API_KEY` | — | Optional Finnhub company-news prefetch (merged with Yahoo/Serper) |
| `FINNHUB_ENABLED` | — | Set `false` to disable Finnhub even when a key is set (default: `true`) |
| `FINNHUB_NEWS_LOOKBACK_DAYS` | — | Days of Finnhub news history per instrument (default: `14`, max `30`) |
| `OPENFIGI_API_KEY` | — | Higher ISIN-resolution rate limits |
| `REPORT_LANGUAGE` | — | Briefing **body** language: `English` or `Italian` (section headings stay English) |
| `FR_MODEL_PROFILE` | — | Model lineup — see [Model profiles](#model-profiles) and [`model_profiles.yaml`](src/financial_researcher/defaults/model_profiles.yaml) |
| `GROQ_API_KEY` | — | Required for `--model-profile free_groq` (no OpenAI key needed) |
| `OPENROUTER_API_KEY` | — | Required for `free_openrouter_nex` or any `openrouter_auto_*` profile |
| `OPENROUTER_AUTO_TRADEOFF` | — | Override profile savings `1`–`10` for `openrouter_auto_*` (1 = quality, 10 = max savings). Beats profile preset; same as `--openrouter-tradeoff` |
| `FR_MODEL_*` | — | Per-agent model override (e.g. `FR_MODEL_CHIEF`) — beats the active profile |
| `WATCHLIST_PATH` | — | Override watchlist YAML location (default: `./config/watchlist.yaml`) |
| `FINANCIAL_RESEARCHER_CONFIG_DIR` | — | Global user config directory (default: `~/.config/financial_researcher`) |
| `FINANCIAL_RESEARCHER_HOME` | — | Base directory for `output/` and `data/` (default: current working directory) |
| `BRIEFING_QUIET` | — | Set `1` to hide CrewAI agent/task progress (same as `--quiet`) |
| `RESEND_API_KEY` | — | [Resend](https://resend.com) API key for `--email` delivery |
| `BRIEFING_EMAIL_FROM` | — | Verified sender, e.g. `Financial Researcher <onboarding@resend.dev>` |
| `BRIEFING_EMAIL_TO` | — | Recipient(s), comma-separated |
| `BRIEFING_EMAIL_SUBJECT_PREFIX` | — | Subject prefix (default: `[Watchlist]`) |
| `BRIEFING_EMAIL_AUTO` | — | Set `1` to email after every run (same as always passing `--email`) |
| `BRIEFING_RUN_METADATA` | — | Set `0` to hide the run-metadata footer (enabled by default) |
| `BRIEFING_CHARTS` | — | Set `0` to skip the embedded performance charts (enabled by default) |

\*Not required for single-provider profiles that use another backend (`anthropic_balanced`, `deepseek_balanced`, `free_*`, `openrouter_auto_*`). `mixed_balanced` needs OpenAI + Anthropic + DeepSeek.

## Usage

```bash
uv run briefing                              # auto session, default language
uv run briefing --session close              # explicit Milan session
uv run briefing --force --language Italian   # Italian prose + tables; headings stay English
uv run briefing --model-profile openai_frontier   # all gpt-5.5 lineup
uv run briefing --watchlist path/to.yaml     # custom watchlist
uv run briefing --email                      # send HTML briefing via Resend
```

| Flag | Description |
|------|-------------|
| `--session` | `pre_open` · `post_open` · `midday` · `close` (default: inferred from clock) |
| `--language LANG` | Body language: `English` or `Italian` (default: English). Headings and UI labels remain English. |
| `--force` | Refresh cached identity and market data |
| `--watchlist PATH` | Watchlist YAML path (default: `config/watchlist.yaml`) |
| `--model-profile` | See [Model profiles](#model-profiles) (default: `openai_balanced`) |
| `--quiet` | Hide CrewAI agent/task progress (default: shown) |
| `--email` | Send the briefing as HTML via Resend (requires env vars below) |
| `--no-run-metadata` | Omit the run-metadata footer (time, models, tokens) from the briefing |
| `--no-charts` | Skip the embedded performance charts (session-aware: intraday/week at midday, full set at close) |
| `--openrouter-tradeoff` | Override OpenRouter Auto savings `1`–`10` (beats profile preset; only for `openrouter_auto_*`) |

By default each briefing ends with a **run-metadata** section: processing time, model profile, token usage and per-agent LLM lineup. Disable with `--no-run-metadata` or `BRIEFING_RUN_METADATA=0`.

### Performance charts

Each briefing embeds a **performance heatmap** (ticker × horizons, green/red), a **risk/return scatter** (30-day volatility vs YTD), **watchlist breadth donuts** (advancing vs declining on 1D/1W), and **indexed-to-100** line charts (white background, editorial palette) in the Performance section. The set depends on the Milan **session**:

| Session | Heatmap columns | Cross-sectional | Line charts |
|---------|-----------------|-----------------|-------------|
| `pre_open` | 1W · 1M · YTD | Scatter · breadth donut (1W) | Weekly |
| `post_open`, `midday` | 1D · 1W · 1M · YTD | Scatter · breadth donuts (1D + 1W) | Intraday + weekly |
| `close` | 1D · 1W · 1M · YTD | Scatter · breadth donuts (1D + 1W) | Session, weekly, monthly, 12-month |

Charts are rendered deterministically in Python ([`chart_generator.py`](src/financial_researcher/services/chart_generator.py)) from Yahoo daily closes and 5-minute intraday bars — **the LLMs never receive the price series or the images**, so they add zero token cost. PNGs are written to `output/briefings/charts/` and referenced from the markdown; when emailing, they are embedded inline via Resend CID attachments. Disable with `--no-charts` or `BRIEFING_CHARTS=0`.

### Email delivery (Resend)

After each run, optionally email the briefing as **HTML** (with the `.md` file attached). Configure in `.env`:

```env
RESEND_API_KEY=re_...
BRIEFING_EMAIL_FROM=Financial Researcher <onboarding@resend.dev>
BRIEFING_EMAIL_TO=you@example.com
# BRIEFING_EMAIL_TO=you@example.com,colleague@example.com
# BRIEFING_EMAIL_AUTO=1
```

```bash
uv run briefing --session close --email
```

`BRIEFING_EMAIL_FROM` must be a **verified sender** in your Resend account (use `onboarding@resend.dev` for initial testing). Recipients live in `BRIEFING_EMAIL_TO` only — one address or several comma-separated. Set `BRIEFING_EMAIL_AUTO=1` to send after every run without passing `--email`.

## Configuration

Two directories — different roles:

| Path | Role |
|------|------|
| **`./config/`** | Your data: `watchlist.yaml` ([`config/README.md`](config/README.md)) |
| **`src/financial_researcher/defaults/`** | Shipped app defaults: agents, tasks, settings, model profiles, Milan sessions |

Application defaults live in `src/financial_researcher/defaults/settings.yaml` (language, scrape behaviour, model profiles, etc.). English section titles and UI labels are defined in [`localization.py`](src/financial_researcher/localization.py). Your watchlist lives in `./config/watchlist.yaml`.

### Language

| What | Controlled by |
|------|----------------|
| Section headings (`## Executive Summary`, …) | Always **English** — [`localization.py`](src/financial_researcher/localization.py) |
| Run-metadata footer, chart subsection titles | Always **English** |
| Briefing prose, performance-table column labels, number formatting | `--language` / `REPORT_LANGUAGE` / `default_language` — `English` or `Italian` |

`REPORT_LANGUAGE` in `.env` overrides `default_language` in `settings.yaml`. Optional per-watchlist override: `language: Italian` in `watchlist.yaml`.

Italian samples in [`examples/briefings/`](examples/briefings/) use Italian body text with the same English section structure as the English sample (`watchlist_2026-06-12_close_en.md`).

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

The briefing is **session-aware**: the same watchlist produces a different memo depending on where you are in the Borsa Italiana day (Europe/Rome). When `--session` is omitted, the CLI picks the most recently passed slot ([schedule](src/financial_researcher/defaults/sessions_milan.yaml)). **On weekends and Borsa Italiana trading holidays the exchange is closed, so the CLI always defaults to `close`** (the last available close). Recognised full-closure holidays: New Year's Day, Good Friday, Easter Monday, Labour Day, Christmas Day and St. Stephen's Day (Easter is computed per year; other Italian civic holidays do not close the exchange).

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
# language: Italian          # optional body-language override for this watchlist
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

| Agent | Role | Model (`openai_balanced`) | Tools |
|-------|------|-------|-------|
| `market_analyst` | Relative performance across the watchlist | gpt-5.4-mini | Pre-loaded context |
| `news_analyst` | News & catalysts behind recent moves | gpt-5.5 | Serper · Yahoo news · scraping |
| `outlook_analyst` | 3–12 month macro & thematic outlook | gpt-5.4 | Serper · scraping |
| `calendar_analyst` | Catalysts in the next 2–4 weeks | gpt-5.4-mini | Serper · scraping |
| `chief_strategist` | Synthesises the final executive memo | gpt-5.5 | — |

Config: [`agents_briefing.yaml`](src/financial_researcher/defaults/agents_briefing.yaml) · [`tasks_briefing.yaml`](src/financial_researcher/defaults/tasks_briefing.yaml) · [`model_profiles.yaml`](src/financial_researcher/defaults/model_profiles.yaml) · [`agent_llm.py`](src/financial_researcher/agent_llm.py)

### Model profiles

Agents route through [LiteLLM](https://docs.litellm.ai/docs/providers) (via CrewAI). The briefing pipeline works with **OpenAI**, **Anthropic**, **DeepSeek**, **Groq**, and **OpenRouter** — pick a profile or override individual agents with `FR_MODEL_*`.

Profiles follow `{provider}_{tier}` naming. **Free tiers** use the `free_` prefix (zero LLM cost); the CLI and run metadata show `[FREE]` when active.

| Profile | API keys needed | Lineup (summary) |
|---------|-----------------|------------------|
| **OpenAI (paid)** | | |
| `openai_balanced` | `OPENAI_API_KEY` | **Default** — mini on market/calendar, `gpt-5.4` outlook, `gpt-5.5` news + chief |
| `openai_frontier` | `OPENAI_API_KEY` | all `gpt-5.5`, higher reasoning on news/chief |
| `openai_economy` | `OPENAI_API_KEY` | mini on all analysts, `gpt-5.4` chief |
| **Single-provider (paid)** | | |
| `anthropic_balanced` | `ANTHROPIC_API_KEY` | Haiku on market/calendar, Sonnet 4.6 on news/chief |
| `deepseek_balanced` | `DEEPSEEK_API_KEY` | V4 Flash on market/outlook, V4 Pro on news/calendar/chief |
| **Multi-provider (paid)** | | |
| `mixed_balanced` | OpenAI + Anthropic + DeepSeek | Flash market · Sonnet news · `gpt-5.4` outlook · V4 Pro calendar · `gpt-5.5` chief |
| **Free (zero LLM cost)** | | |
| `free_groq` | `GROQ_API_KEY` | Llama via Groq — experimental |
| `free_openrouter_nex` | `OPENROUTER_API_KEY` | [Nex-N2-Pro (free)](https://openrouter.ai/nex-agi/nex-n2-pro:free) — experimental |
| **OpenRouter Auto (paid, variable cost)** | | |
| `openrouter_auto_quality` | `OPENROUTER_API_KEY` | Auto Router — savings **1** (top quality) |
| `openrouter_auto_balanced` | `OPENROUTER_API_KEY` | Auto Router — savings **7** (balanced) |
| `openrouter_auto_economy` | `OPENROUTER_API_KEY` | Auto Router — savings **10** (max savings) |

```bash
uv run briefing --model-profile deepseek_balanced        # DeepSeek only
uv run briefing --model-profile mixed_balanced           # OpenAI + Anthropic + DeepSeek
uv run briefing --model-profile anthropic_balanced       # Claude Haiku + Sonnet 4.6
uv run briefing --model-profile free_openrouter_nex      # [FREE] Nex-N2-Pro
uv run briefing --model-profile openrouter_auto_quality
uv run briefing --model-profile openrouter_auto_balanced
uv run briefing --model-profile openrouter_auto_economy --openrouter-tradeoff 8
uv run briefing --model-profile openai_economy
export FR_MODEL_PROFILE=openai_frontier
```

Set `model_profile: openai_economy` in `defaults/settings.yaml` for a persistent default. Per-agent `FR_MODEL_*` env vars still override one slot in the active profile.

> [!NOTE]
> **Provider notes**
> - **`deepseek_balanced`** — [DeepSeek V4](https://api-docs.deepseek.com/) via `deepseek/deepseek-v4-flash` and `deepseek/deepseek-v4-pro`. Set `DEEPSEEK_API_KEY` only.
> - **`mixed_balanced`** — assigns each provider where it fits best: cheap DeepSeek for table analysts, Anthropic for news synthesis, OpenAI for outlook + final memo. All three API keys required.
> - **`anthropic_balanced`** — [Claude Haiku 4.5](https://www.anthropic.com/news/claude-haiku-4-5) + [Sonnet 4.6](https://docs.litellm.ai/docs/providers/anthropic).
> - **`free_*`** — zero LLM token cost; experimental; weaker citations than `openai_balanced`. Shown as `[FREE]` in logs and run metadata.
> - **`openrouter_auto_*`** — [OpenRouter Auto Router](https://openrouter.ai/docs/guides/routing/routers/auto-router): savings level is set on the profile (`quality`=1, `balanced`=7, `economy`=10). Override with `OPENROUTER_AUTO_TRADEOFF` or `--openrouter-tradeoff`. The actual routed model is chosen by OpenRouter per request.

> [!WARNING]
> **Default profile (`openai_balanced`) targets cost vs quality.** Analyst agents emit terse internal handoffs; reasoning effort is tuned per agent — together this typically cuts completion tokens by roughly half versus `openai_frontier`. A full run still makes many LLM calls plus news search and page scraping.
>
> **Want all-frontier quality?** Use `--model-profile openai_frontier` or per-agent overrides (see `.env.sample`).

**Prompt caching:** agent role/goal/backstory in `agents_briefing.yaml` are static (no dates or session placeholders). Run-specific tables and dates are appended at the end of each task description under `--- RUN CONTEXT ---`, so OpenAI can cache the shared instruction prefix across runs.

<details>
<summary><b>Briefing structure</b></summary>

Title block → Executive Summary → Performance Snapshot → What's Driving the Moves → Medium-Term Outlook → Event Calendar → Correlated Themes → Risks & Watchpoints → References → Disclaimer. **Section headings are always English.** With `--language Italian`, narrative prose and performance-table labels use Italian; post-process also normalizes any legacy Italian headings to English.
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
│   ├── localization.py     # English section headings and UI labels
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

### Tests

```bash
uv run pytest -q
```

When you add or remove tests, refresh the README badge (committed manually — CI no longer pushes to `main`):

```bash
uv run python scripts/update_test_badge.py
git add .github/badges/tests.json
```

CI runs `scripts/update_test_badge.py --check` and fails if the badge is stale.

## Acknowledgements

Extends CrewAI patterns from **Ed Donner's** [AI Engineer Agentic Track](https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/). Details in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

## Author

**Luca Amore** — [GitHub](https://github.com/lookee) · [lucaamore.com](https://www.lucaamore.com) · [LinkedIn](https://www.linkedin.com/in/lucaamore)

## Disclaimer

**Experimental** coursework extension — *as is*, no warranty. **Not financial advice**: briefings are informational only; verify against primary sources. You are responsible for API costs and third-party terms.

## License

Public domain. See [LICENSE](LICENSE).
