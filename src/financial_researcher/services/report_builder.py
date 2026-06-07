"""Build pre-formatted report sections and CrewAI inputs from market snapshots."""

import json
from typing import Any

from financial_researcher.models.instrument import InstrumentIdentity
from financial_researcher.services.holding_labels import holding_synopsis
from financial_researcher.settings import get_default_language

_SECTOR_LABELS_IT: dict[str, str] = {
    "technology": "Tecnologia",
    "communication_services": "Telecomunicazioni",
    "financial_services": "Servizi finanziari",
    "consumer_cyclical": "Consumi ciclici",
    "consumer_defensive": "Consumi difensivi",
    "healthcare": "Sanità",
    "industrials": "Industriali",
    "basic_materials": "Materie prime",
    "energy": "Energia",
    "utilities": "Utilities",
    "realestate": "Immobiliare",
}

_SECTOR_LABELS_EN: dict[str, str] = {
    "technology": "Technology",
    "communication_services": "Communication Services",
    "financial_services": "Financial Services",
    "consumer_cyclical": "Consumer Cyclical",
    "consumer_defensive": "Consumer Defensive",
    "healthcare": "Healthcare",
    "industrials": "Industrials",
    "basic_materials": "Basic Materials",
    "energy": "Energy",
    "utilities": "Utilities",
    "realestate": "Real Estate",
}


def _is_italian(language: str) -> bool:
    return language.lower().startswith("it")


def _resolve_language(language: str | None) -> str:
    return language or get_default_language()


def _na(language: str) -> str:
    return "n/d" if _is_italian(language) else "n/a"


def _fmt_num(value: float | int | None, decimals: int = 2, language: str = "English") -> str:
    if value is None:
        return _na(language)
    formatted = f"{value:,.{decimals}f}"
    if _is_italian(language):
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def _fmt_pct(value: float | None, language: str = "English") -> str:
    if value is None:
        return _na(language)
    return f"{_fmt_num(value, language=language)}%"


def _fmt_large(value: float | int | None, language: str = "English") -> str:
    if value is None:
        return _na(language)
    if value >= 1_000_000_000_000:
        return f"{_fmt_num(value / 1_000_000_000_000, language=language)} T"
    if value >= 1_000_000_000:
        suffix = " Mld" if _is_italian(language) else " B"
        return f"{_fmt_num(value / 1_000_000_000, language=language)}{suffix}"
    if value >= 1_000_000:
        suffix = " Mln" if _is_italian(language) else " M"
        return f"{_fmt_num(value / 1_000_000, language=language)}{suffix}"
    return _fmt_num(value, language=language)


def _fmt_yield(value: float | None, language: str = "English") -> str:
    if value is None:
        return _na(language)
    if abs(value) < 1:
        return _fmt_pct(value * 100, language=language)
    return _fmt_pct(value, language=language)


def _sector_label(key: str, language: str) -> str:
    labels = _SECTOR_LABELS_IT if _is_italian(language) else _SECTOR_LABELS_EN
    return labels.get(key, key.replace("_", " ").title())


def _labels(language: str) -> dict[str, str]:
    if _is_italian(language):
        return {
            "preloaded_header": "=== DATI DI MERCATO PRE-CARICATI (Yahoo Finance) ===",
            "source_line": "Fonte [1]: Yahoo Finance, {date}, {url}",
            "key_metrics": "## Numeri chiave (includere nel report)",
            "performance": "## Andamento (includere nel report)",
            "etf_profile": "## Profilo ETF (includere nel report)",
            "issuer": "Emittente",
            "fund_family": "Famiglia",
            "fundamentals": "## Ultimi dati fondamentali (includere nel report)",
            "eps": "EPS",
            "revenue": "Ricavi",
            "profit_margin": "Margine di profitto",
            "forecasts": "## Previsioni e consensus (includere nel report)",
            "forecasts_short": "## Previsioni e consensus",
            "target_mean": "Target medio",
            "target_range": "Target min/max",
            "recommendation": "Raccomandazione",
            "analysts": "Analisti",
            "data_unavailable": "Dati non disponibili nelle fonti consultate.",
            "profile": "## Profilo (includere in Cos'è)",
            "end_marker": "=== FINE DATI DI MERCATO ===",
            "limitations": "## Limitazioni dei dati (copiare verbatim nel report)",
            "holdings": "## Principali posizioni — top {count} (includere nel report)",
            "holdings_intro": (
                "Elenco parziale: Yahoo Finance espone solo le {count} posizioni più rilevanti. "
                "Il fondo include altri titoli non elencati di seguito "
                "(peso combinato stimato: {other_weight}%) [1]."
            ),
            "holdings_weight_summary": (
                "**Peso combinato top {count}:** {top_total} [1] · "
                "**Altri titoli non elencati (stima):** {other_weight} [1]"
            ),
            "holdings_source": "Fonte composizione: Yahoo Finance, {date} [1]",
            "holdings_table": "| Società | Peso | In sintesi |",
            "sector_weights": "**Pesi settoriali:** [1]",
            "etf_table": "| Prezzo | Variazione | AUM | TER | Rendimento | Categoria |",
            "stock_table": "| Prezzo | Variazione | Capitalizzazione | P/E | Dividendo | Beta |",
            "market_data_source": (
                "Dati di mercato da Yahoo Finance; possono differire da KID/prospetto dell'emittente."
            ),
            "ter_missing": "TER non disponibile su Yahoo Finance per questo ETF.",
            "yield_missing": "Rendimento/distribuzione non disponibile su Yahoo Finance.",
            "category_missing": "Categoria fondo non disponibile su Yahoo Finance.",
            "description_missing": "Descrizione ufficiale del fondo non disponibile su Yahoo Finance.",
            "holdings_partial": (
                "Composizione limitata alle top 10 posizioni disponibili su Yahoo Finance; "
                "non include l'elenco completo del portafoglio."
            ),
            "holdings_synopsis_note": (
                "Sintesi delle singole società derivate da settore e industria Yahoo."
            ),
            "holdings_missing": "Composizione del portafoglio non disponibile su Yahoo Finance.",
            "forecasts_missing": "Previsioni e consensus analisti non disponibili su Yahoo Finance.",
            "news_window": "Notizie limitate alle ultime 72 ore dalla ricerca automatica.",
        }

    return {
        "preloaded_header": "=== PRE-LOADED MARKET DATA (Yahoo Finance) ===",
        "source_line": "Source [1]: Yahoo Finance, {date}, {url}",
        "key_metrics": "## Key metrics (include in report)",
        "performance": "## Performance (include in report)",
        "etf_profile": "## ETF profile (include in report)",
        "issuer": "Issuer",
        "fund_family": "Fund family",
        "fundamentals": "## Latest fundamentals (include in report)",
        "eps": "EPS",
        "revenue": "Revenue",
        "profit_margin": "Profit margin",
        "forecasts": "## Forecasts and consensus (include in report)",
        "forecasts_short": "## Forecasts and consensus",
        "target_mean": "Mean target",
        "target_range": "Target low/high",
        "recommendation": "Recommendation",
        "analysts": "Analysts",
        "data_unavailable": "Data not available in the sources consulted.",
        "profile": "## Profile (include in What it is)",
        "end_marker": "=== END MARKET DATA ===",
        "limitations": "## Data limitations (copy verbatim into report)",
        "holdings": "## Top {count} holdings (include in report)",
        "holdings_intro": (
            "Partial list: Yahoo Finance shows only the largest {count} positions. "
            "The ETF holds additional securities not listed below "
            "(estimated combined weight: {other_weight}%) [1]."
        ),
        "holdings_weight_summary": (
            "**Combined weight of top {count}:** {top_total} [1] · "
            "**Other holdings not listed (est.):** {other_weight} [1]"
        ),
        "holdings_source": "Composition source: Yahoo Finance, {date} [1]",
        "holdings_table": "| Company | Weight | Summary |",
        "sector_weights": "**Sector weights:** [1]",
        "etf_table": "| Price | Change | AUM | TER | Yield | Category |",
        "stock_table": "| Price | Change | Market cap | P/E | Dividend | Beta |",
        "market_data_source": (
            "Market data from Yahoo Finance; may differ from the issuer KID/prospectus."
        ),
        "ter_missing": "Expense ratio not available on Yahoo Finance for this ETF.",
        "yield_missing": "Yield/distribution not available on Yahoo Finance.",
        "category_missing": "Fund category not available on Yahoo Finance.",
        "description_missing": "Official fund description not available on Yahoo Finance.",
        "holdings_partial": (
            "Composition limited to the top 10 holdings available on Yahoo Finance; "
            "does not include the full portfolio list."
        ),
        "holdings_synopsis_note": (
            "Individual company summaries derived from Yahoo sector and industry data."
        ),
        "holdings_missing": "Portfolio composition not available on Yahoo Finance.",
        "forecasts_missing": "Analyst forecasts and consensus not available on Yahoo Finance.",
        "news_window": "News limited to the last 72 hours from automated search.",
    }


def format_market_context(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, indent=2, ensure_ascii=False)


def format_identity_context(identity: InstrumentIdentity) -> str:
    return json.dumps(identity.to_dict(), indent=2, ensure_ascii=False)


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value in {"n/d", "n/a"}


def format_data_limitations(snapshot: dict[str, Any], language: str | None = None) -> str:
    """Auto-generated data limitations section for the composer."""
    report_language = _resolve_language(language)
    text = _labels(report_language)
    instrument_type = snapshot.get("instrument_type", "stock")
    fundamentals = snapshot.get("fundamentals", {})
    profile = snapshot.get("profile", {})
    holdings = snapshot.get("holdings")
    limitations: list[str] = [text["market_data_source"]]

    if instrument_type == "etf":
        if _is_missing(fundamentals.get("expense_ratio")):
            limitations.append(text["ter_missing"])
        if _is_missing(fundamentals.get("yield")):
            limitations.append(text["yield_missing"])
        if _is_missing(fundamentals.get("category")):
            limitations.append(text["category_missing"])
        if _is_missing(profile.get("description")):
            limitations.append(text["description_missing"])
        if holdings and holdings.get("top_holdings"):
            limitations.append(text["holdings_partial"])
            limitations.append(text["holdings_synopsis_note"])
        elif not holdings:
            limitations.append(text["holdings_missing"])
    elif not snapshot.get("forecasts"):
        limitations.append(text["forecasts_missing"])

    limitations.append(text["news_window"])

    lines = [text["limitations"]]
    for item in limitations:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def format_holdings_summary(snapshot: dict[str, Any], language: str | None = None) -> str:
    """Pre-formatted ETF holdings section with [1] citations."""
    report_language = _resolve_language(language)
    text = _labels(report_language)
    holdings = snapshot.get("holdings")
    if not holdings or not holdings.get("top_holdings"):
        return ""

    ref = "[1]"
    top_holdings = holdings["top_holdings"]
    count = holdings.get("holdings_count") or len(top_holdings)
    top_weight_total = holdings.get("top_weight_total")
    if top_weight_total is None:
        top_weight_total = round(
            sum(item.get("weight") or 0 for item in top_holdings),
            2,
        )
    other_weight = holdings.get("other_weight_estimate")
    if other_weight is None:
        other_weight = round(max(0.0, 100.0 - top_weight_total), 2)

    lines = [
        text["holdings"].format(count=count),
        "",
        text["holdings_intro"].format(
            count=count,
            other_weight=_fmt_num(other_weight, language=report_language),
        ),
        "",
        text["holdings_source"].format(date=snapshot.get("fetched_on", "")),
        "",
        text["holdings_table"],
        "|---------|------|------------|",
    ]

    for item in top_holdings:
        name = item.get("name") or item.get("symbol") or _na(report_language)
        weight = _fmt_pct(item.get("weight"), language=report_language)
        description = holding_synopsis(
            item.get("sector"),
            item.get("industry"),
            language=report_language,
        )
        lines.append(f"| {name} | {weight} {ref} | {description} {ref} |")

    lines.extend(
        [
            "",
            text["holdings_weight_summary"].format(
                count=count,
                top_total=_fmt_pct(top_weight_total, language=report_language),
                other_weight=_fmt_pct(other_weight, language=report_language),
            ),
        ]
    )

    sector_weights = holdings.get("sector_weightings") or {}
    if sector_weights:
        lines.append("")
        lines.append(text["sector_weights"])
        sorted_sectors = sorted(
            sector_weights.items(), key=lambda item: item[1], reverse=True
        )
        for key, weight in sorted_sectors:
            if weight > 0:
                lines.append(
                    f"- {_sector_label(key, report_language)}: "
                    f"{_fmt_pct(weight, language=report_language)} {ref}"
                )

    lines.append("")
    return "\n".join(lines)


def format_market_summary(
    snapshot: dict[str, Any],
    identity: InstrumentIdentity,
    language: str | None = None,
) -> str:
    """Pre-formatted market sections with [1] citations for the composer."""
    report_language = _resolve_language(language)
    text = _labels(report_language)
    ref = "[1]"
    price = snapshot.get("price", {})
    perf = snapshot.get("performance", {})
    profile = snapshot.get("profile", {})
    fundamentals = snapshot.get("fundamentals", {})
    forecasts = snapshot.get("forecasts")
    currency = price.get("currency") or identity.currency or "EUR"
    instrument_type = snapshot.get("instrument_type", identity.instrument_type)
    na = _na(report_language)

    lines = [
        text["preloaded_header"],
        text["source_line"].format(
            date=snapshot.get("fetched_on", ""),
            url=snapshot.get("source_url", ""),
        ),
        "",
    ]

    if instrument_type == "etf":
        fund_family = fundamentals.get("fund_family") or identity.issuer or na
        lines += [
            text["key_metrics"],
            text["etf_table"],
            "|--------|------------|-----|-----|------------|-----------|",
            (
                f"| {_fmt_num(price.get('current'), language=report_language)} {currency} {ref} "
                f"| {_fmt_pct(price.get('change_percent'), language=report_language)} {ref} "
                f"| {_fmt_large(fundamentals.get('aum'), language=report_language)} {ref} "
                f"| {_fmt_yield(fundamentals.get('expense_ratio'), language=report_language)} {ref} "
                f"| {_fmt_yield(fundamentals.get('yield'), language=report_language)} {ref} "
                f"| {fundamentals.get('category') or na} {ref} |"
            ),
            "",
            text["performance"],
        ]
    else:
        lines += [
            text["key_metrics"],
            text["stock_table"],
            "|--------|------------|------------------|-----|-----------|------|",
            (
                f"| {_fmt_num(price.get('current'), language=report_language)} {currency} {ref} "
                f"| {_fmt_pct(price.get('change_percent'), language=report_language)} {ref} "
                f"| {_fmt_large(profile.get('market_cap'), language=report_language)} {ref} "
                f"| {_fmt_num(fundamentals.get('pe_ratio'), language=report_language)} {ref} "
                f"| {_fmt_yield(fundamentals.get('dividend_yield'), language=report_language)} {ref} "
                f"| {_fmt_num(profile.get('beta'), language=report_language)} {ref} |"
            ),
            "",
            text["performance"],
        ]

    for period in ("1d", "1w", "1m", "3m", "6m", "1y", "ytd"):
        label = period.upper() if period != "ytd" else "YTD"
        lines.append(
            f"- **{label}:** {_fmt_pct(perf.get(period), language=report_language)} {ref}"
        )

    lines.append("")

    if instrument_type == "etf":
        fund_family = fundamentals.get("fund_family") or identity.issuer or na
        lines += [
            text["etf_profile"],
            f"- {text['issuer']}: {fund_family} {ref}",
            f"- {text['fund_family']}: {fund_family} {ref}",
            "",
        ]
        holdings_block = format_holdings_summary(snapshot, language=report_language)
        if holdings_block:
            lines.append(holdings_block)
        lines.append(format_data_limitations(snapshot, language=report_language))
    elif instrument_type == "stock":
        profit_margins = fundamentals.get("profit_margins")
        if profit_margins is not None and abs(profit_margins) < 1:
            profit_margins = profit_margins * 100

        lines += [
            text["fundamentals"],
            f"- {text['eps']}: {_fmt_num(fundamentals.get('eps'), language=report_language)} {ref}",
            f"- {text['revenue']}: {_fmt_large(fundamentals.get('revenue'), language=report_language)} {ref}",
            f"- {text['profit_margin']}: {_fmt_pct(profit_margins, language=report_language)} {ref}",
            "",
        ]
        if forecasts:
            lines += [
                text["forecasts"],
                f"- {text['target_mean']}: {_fmt_num(forecasts.get('target_mean'), language=report_language)} {currency} {ref}",
                f"- {text['target_range']}: {_fmt_num(forecasts.get('target_low'), language=report_language)} / {_fmt_num(forecasts.get('target_high'), language=report_language)} {currency} {ref}",
                f"- {text['recommendation']}: {forecasts.get('recommendation') or na} {ref}",
                f"- {text['analysts']}: {forecasts.get('analyst_count') or na} {ref}",
                "",
            ]
        else:
            lines += [
                text["forecasts_short"],
                text["data_unavailable"],
                "",
            ]
        lines.append(format_data_limitations(snapshot, language=report_language))

    description = profile.get("description")
    if description:
        lines += [
            text["profile"],
            f"{description[:800]}{'...' if len(description) > 800 else ''} {ref}",
            "",
        ]

    lines.append(text["end_marker"])
    return "\n".join(lines)


def build_crew_inputs(
    identity: InstrumentIdentity,
    snapshot: dict[str, Any],
    language: str | None = None,
) -> dict[str, str]:
    from datetime import date

    report_language = _resolve_language(language)

    return {
        "isin": identity.isin,
        "company": identity.name,
        "ticker": identity.primary_ticker,
        "instrument_type": identity.instrument_type,
        "language": report_language,
        "current_date": date.today().isoformat(),
        "identity_context": format_identity_context(identity),
        "market_context": format_market_context(snapshot),
        "market_summary": format_market_summary(snapshot, identity, language=report_language),
    }


def output_path_for(identity: InstrumentIdentity) -> str:
    safe_ticker = identity.primary_ticker.replace(".", "_")
    from datetime import date

    return f"output/reports/{identity.isin}_{safe_ticker}_{date.today().isoformat()}.md"
