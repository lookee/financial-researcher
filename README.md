# Financial Researcher

![Python](https://img.shields.io/badge/python-3.10--3.12-3776AB?logo=python&logoColor=white)
![CrewAI](https://img.shields.io/badge/CrewAI-multi--agent-8957E5?logo=openai&logoColor=white)
![Status](https://img.shields.io/badge/status-experimental-red)

A [CrewAI](https://crewai.com) multi-agent CLI that generates Markdown research reports for **stocks and ETFs** from an **ISIN** code. Market data, ETF holdings, and report structure are fetched deterministically in Python; two LLM agents handle news research and final composition.

## Author

Created by **Luca Amore**.

- Email: [luca.amore@gmail.com](mailto:luca.amore@gmail.com)
- GitHub: [@lookee](https://github.com/lookee)
- Website: [lucaamore.com](https://www.lucaamore.com)
- LinkedIn: [lucaamore](https://www.linkedin.com/in/lucaamore)

This code is **free to use, copy, modify, and redistribute for any purpose**, without restrictions.

## Acknowledgements

This project is a **fork and extension** of the CrewAI patterns taught in **Ed Donner's** Udemy course:

**[AI Engineer Agentic Track: The Complete Agent & MCP Course](https://www.udemy.com/course/the-complete-agentic-ai-engineering-course/)**

The original course codebase demonstrated multi-agent crews, tasks, and tools. This repository adapts that foundation for ISIN-based financial research: instrument resolution, Yahoo Finance snapshots, ETF portfolio composition, cached identity/market data, and structured report templates for stocks vs ETFs.

Thank you to **Ed Donner** for the excellent agentic AI engineering curriculum.

## Architecture

```
ISIN + ticker
    │
    ├─ IsinResolver        (OpenFIGI + Yahoo Finance)
    ├─ MarketDataService   (prices, performance, ETF holdings)
    └─ report_builder      (pre-formatted market_summary → citation [1])
            │
            ▼
    CrewAI (sequential)
    ├─ news_researcher     (Serper, Yahoo News → citations [2+])
    └─ report_composer     (final Markdown report)
```

## Requirements

- Python 3.10–3.12
- [uv](https://github.com/astral-sh/uv) (recommended)

## Setup

```bash
pip install uv
uv sync
cp .env.sample .env
# Add OPENAI_API_KEY and SERPER_API_KEY to .env
```

## Commands

```bash
# Generate a report (ISIN + exchange ticker)
uv run report US67066G1040 NVDA

# ETF example
uv run report IE00BK5BQT80 VWCE.DE

# ISIN only (uses cached identity if available)
uv run report US67066G1040

# Resolve and cache instrument identity
uv run resolve US67066G1040 NVDA

# Batch reports from watchlist.yaml
uv run watchlist

# Regenerate all reports already present in output/reports/
uv run refresh-reports
```

Optional flags: `--force`, `--type stock|etf`.

## Report language

Default: **English**.

- Global default: `default_language` in `src/financial_researcher/config/settings.yaml`
- Override via `.env`: `REPORT_LANGUAGE=Italian`
- Per run: `uv run report US67066G1040 NVDA --language Italian`

## Output

| Path | Description |
|------|-------------|
| `output/reports/{ISIN}_{TICKER}_{DATE}.md` | Generated report |
| `data/identity/{ISIN}.json` | Cached instrument identity |
| `data/market/{ISIN}/latest.json` | Cached market snapshot (1 h TTL) |

## Disclaimer

**Experimental software.** This repository is **experimental code** developed as a personal extension of exercises and patterns from an agentic AI engineering course. It is shared for learning and exploration only — not as a finished, audited, or production-ready product.

**No warranty.** The software is provided **as is**, without guarantees of correctness, completeness, availability, or fitness for any purpose. APIs, data sources, LLM outputs, and dependencies may change or fail without notice. Use it at your own risk.

**Not financial advice.** Generated reports are for **informational and educational purposes only** and do not constitute investment, legal, or tax advice. Market data may be delayed, incomplete, or wrong; LLM-generated text may contain errors or hallucinations. Always verify information against primary sources (issuer KID/prospectus, regulated filings, official exchange data) before making any investment decision.

**Your responsibility.** You are solely responsible for how you use this software, including API costs, compliance with third-party terms of service (OpenAI, Serper, Yahoo Finance, OpenFIGI), and any decisions taken on the basis of generated output.

## License

This project is released into the **public domain**. You may use, modify, and distribute it freely, for any purpose, without restrictions.

See [LICENSE](LICENSE). Course-derived patterns remain attributed to Ed Donner's Udemy material as described in [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).
