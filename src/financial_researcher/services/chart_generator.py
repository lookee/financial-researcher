"""Generate elegant, deterministic performance charts for briefings.

Charts are rendered in pure Python (matplotlib, Agg backend) from price series
fetched by the market pipeline. They never touch the LLMs: the crew receives no
price series and no images — charts are produced after the crew has run and
injected into the final markdown / email.

Horizons are chosen per Milan session:
  pre_open   → current week (no intraday yet)
  post_open, midday → intraday + current week
  close      → session (intraday), week, month, year
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

from financial_researcher.services import chart_theme

# Horizon -> trailing daily sessions (None = year-to-date slice).
_HORIZON_SESSIONS: dict[str, int | None] = {
    "1w": 5,
    "1m": 21,
    "ytd": None,
    "1y": 252,
}

# Chart set per Milan session (aligned with session_profiles valid_metrics).
_SESSION_CHART_HORIZONS: dict[str, tuple[str, ...]] = {
    "pre_open": ("1w",),
    "post_open": ("1d", "1w"),
    "midday": ("1d", "1w"),
    "close": ("1d", "1w", "1m", "1y"),
}

# Performance heatmap columns (cross-sectional snapshot, session-aware).
_SESSION_HEATMAP_COLUMNS: dict[str, tuple[str, ...]] = {
    "pre_open": ("1w", "1m", "ytd"),
    "post_open": ("1d", "1w", "1m", "ytd"),
    "midday": ("1d", "1w", "1m", "ytd"),
    "close": ("1d", "1w", "1m", "ytd"),
}

_HEATMAP_COLUMN_LABELS: dict[str, tuple[str, str]] = {
    "1d": ("Giorn.", "1D"),
    "1w": ("Sett.", "1W"),
    "1m": ("Mese", "1M"),
    "ytd": ("YTD", "YTD"),
}

# Watchlist breadth chart metrics per session (advancing vs declining counts).
_SESSION_BREADTH_METRICS: dict[str, tuple[str, ...]] = {
    "pre_open": ("1w",),
    "post_open": ("1d", "1w"),
    "midday": ("1d", "1w"),
    "close": ("1d", "1w"),
}

_BREADTH_METRIC_LABELS: dict[str, tuple[str, str]] = {
    "1d": ("Giorn.", "1D"),
    "1w": ("Sett.", "1W"),
}

_MIN_BREADTH_INSTRUMENTS = 2

_MIN_DAILY_POINTS = 3
_MIN_INTRADAY_POINTS = 2


@dataclass(frozen=True)
class ChartArtifact:
    """A rendered chart ready to embed in markdown and email."""

    horizon: str
    caption: str
    path: Path
    content_id: str


def resolve_chart_horizons(session: str) -> tuple[str, ...]:
    """Return chart horizons for a Milan briefing session."""
    return _SESSION_CHART_HORIZONS.get(session, ("1w", "1y"))


def resolve_heatmap_columns(session: str) -> tuple[str, ...]:
    """Return performance heatmap columns for a Milan briefing session."""
    return _SESSION_HEATMAP_COLUMNS.get(session, ("1d", "1w", "1m", "ytd"))


def resolve_breadth_metrics(session: str) -> tuple[str, ...]:
    """Return performance horizons counted in the watchlist breadth chart."""
    return _SESSION_BREADTH_METRICS.get(session, ("1d", "1w"))


def _watchlist_instruments(instruments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in instruments
        if item.get("type") not in ("benchmark",) and item.get("ticker")
    ]


def _heatmap_caption(*, italian: bool, session: str) -> str:
    if session == "pre_open":
        return (
            "Mappa performance — settimana, mese, YTD"
            if italian
            else "Performance heatmap — week, month, YTD"
        )
    if session == "midday":
        return (
            "Mappa performance — giornaliera (parziale), settimana, mese, YTD"
            if italian
            else "Performance heatmap — intraday (partial), week, month, YTD"
        )
    return (
        "Mappa performance — giornaliera, settimana, mese, YTD"
        if italian
        else "Performance heatmap — day, week, month, YTD"
    )


def _fmt_pct_cell(value: float | None, *, italian: bool) -> str:
    if value is None:
        return "n/a"
    sign = "+" if value >= 0 else "−"
    body = f"{abs(value):.1f}%".replace(".", "," if italian else ".")
    return f"{sign}{body}"


def _heatmap_colormap():
    """Diverging green–white–red map centred on zero."""
    return LinearSegmentedColormap.from_list(
        "performance_diverging",
        [chart_theme.NEGATIVE, "#FEE2E2", chart_theme.BACKGROUND, "#D1FAE5", chart_theme.POSITIVE],
        N=256,
    )


def build_performance_heatmap(
    instruments: list[dict[str, Any]],
    *,
    session: str,
    output_path: Path,
    language: str,
    columns: tuple[str, ...] | None = None,
) -> ChartArtifact | None:
    """Render a ticker × horizon performance heatmap. Returns None when insufficient data."""
    italian = language.lower().startswith("ital")
    chosen = columns if columns is not None else resolve_heatmap_columns(session)
    watchlist = _watchlist_instruments(instruments)
    if not watchlist or not chosen:
        return None

    rows: list[dict[str, Any]] = []
    matrix: list[list[float | None]] = []
    for item in watchlist:
        perf = item.get("performance") or {}
        values = [perf.get(key) for key in chosen]
        if not any(v is not None for v in values):
            continue
        sort_key = perf.get("1d") if "1d" in chosen else perf.get("ytd")
        rows.append(
            {
                "ticker": item.get("ticker", "?"),
                "values": values,
                "sort": sort_key if sort_key is not None else float("-inf"),
            }
        )
        matrix.append(values)

    if not rows:
        return None

    rows.sort(key=lambda row: row["sort"], reverse=True)
    matrix = [row["values"] for row in rows]
    tickers = [row["ticker"] for row in rows]

    numeric = [v for row in matrix for v in row if v is not None]
    if not numeric:
        return None

    abs_max = max(abs(min(numeric)), abs(max(numeric)), 0.5)
    norm = TwoSlopeNorm(vmin=-abs_max, vcenter=0.0, vmax=abs_max)
    cmap = _heatmap_colormap()

    col_labels = [
        _HEATMAP_COLUMN_LABELS[key][0 if italian else 1] for key in chosen
    ]
    data = np.array(
        [[float(v) if v is not None else np.nan for v in row] for row in matrix],
        dtype=float,
    )

    row_count = len(tickers)
    fig_height = max(2.8, 0.52 * row_count + 1.4)

    with plt.rc_context(chart_theme.rcparams()):
        fig, ax = plt.subplots(figsize=(8.4, fig_height))
        ax.set_facecolor(chart_theme.BACKGROUND)

        masked = np.ma.masked_invalid(data)
        im = ax.imshow(masked, aspect="auto", cmap=cmap, norm=norm)

        ax.set_xticks(range(len(col_labels)))
        ax.set_xticklabels(col_labels, fontsize=10, color=chart_theme.MUTED)
        ax.set_yticks(range(row_count))
        ax.set_yticklabels(tickers, fontsize=10, fontweight="bold", color=chart_theme.INK)

        for row_idx in range(row_count):
            for col_idx in range(len(chosen)):
                value = matrix[row_idx][col_idx]
                text = _fmt_pct_cell(value, italian=italian)
                cell_color = chart_theme.INK
                if value is not None and abs(value) >= abs_max * 0.55:
                    cell_color = chart_theme.BACKGROUND
                ax.text(
                    col_idx,
                    row_idx,
                    text,
                    ha="center",
                    va="center",
                    fontsize=9,
                    fontweight="600",
                    color=cell_color,
                )

        for edge in range(row_count + 1):
            ax.axhline(edge - 0.5, color=chart_theme.HAIRLINE, linewidth=0.8)
        for edge in range(len(col_labels) + 1):
            ax.axvline(edge - 0.5, color=chart_theme.HAIRLINE, linewidth=0.8)

        ax.tick_params(length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)

        title = _heatmap_caption(italian=italian, session=session)
        ax.set_title(
            title,
            loc="left",
            fontsize=14,
            fontweight="bold",
            color=chart_theme.INK,
            pad=14,
        )

        cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, aspect=18)
        cbar.ax.tick_params(labelsize=8, colors=chart_theme.MUTED)
        cbar.outline.set_visible(False)
        cbar.set_label(
            "%" if not italian else "%",
            fontsize=8,
            color=chart_theme.MUTED,
        )

        source = "Fonte: Yahoo Finance" if italian else "Source: Yahoo Finance"
        fig.text(
            0.01,
            0.01,
            f"Financial Researcher · {source}",
            fontsize=8,
            color=chart_theme.MUTED,
            ha="left",
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, format="png", bbox_inches="tight")
        plt.close(fig)

    return ChartArtifact(
        horizon="heatmap",
        caption=title,
        path=output_path,
        content_id=f"chart-heatmap-{output_path.stem}",
    )


def _risk_return_caption(*, italian: bool) -> str:
    return (
        "Rischio vs rendimento — volatilità 30g e YTD"
        if italian
        else "Risk vs return — 30-day volatility and YTD"
    )


def build_risk_return_scatter(
    instruments: list[dict[str, Any]],
    *,
    session: str,
    output_path: Path,
    language: str,
    return_key: str = "ytd",
) -> ChartArtifact | None:
    """Render a risk/return scatter (30d vol vs YTD). Returns None when insufficient data."""
    _ = session  # reserved for future session-specific return horizons
    italian = language.lower().startswith("ital")
    points: list[dict[str, Any]] = []
    for index, item in enumerate(_watchlist_instruments(instruments)):
        vol = item.get("volatility_30d")
        perf = item.get("performance") or {}
        ytd = perf.get(return_key)
        if vol is None or ytd is None:
            continue
        points.append(
            {
                "ticker": item.get("ticker", "?"),
                "vol": float(vol),
                "return": float(ytd),
                "color": chart_theme.series_color(index),
            }
        )

    if len(points) < 2:
        return None

    vols = [point["vol"] for point in points]
    returns = [point["return"] for point in points]
    vol_min, vol_max = min(vols), max(vols)
    ret_min, ret_max = min(returns), max(returns)
    vol_pad = max((vol_max - vol_min) * 0.12, 1.0)
    ret_pad = max((ret_max - ret_min) * 0.12, 1.0)
    x_lo = max(0.0, vol_min - vol_pad)
    x_hi = vol_max + vol_pad
    y_lo = ret_min - ret_pad
    y_hi = ret_max + ret_pad
    if y_lo < 0 < y_hi:
        y_lo = min(y_lo, -ret_pad * 0.5)
        y_hi = max(y_hi, ret_pad * 0.5)

    title = _risk_return_caption(italian=italian)
    x_label = "Volatilità 30g (%)" if italian else "30-day volatility (%)"
    y_label = "YTD (%)" if italian else "YTD (%)"

    with plt.rc_context(chart_theme.rcparams()):
        fig, ax = plt.subplots(figsize=(8.4, 5.2))
        chart_theme.style_axes(ax)

        for point in points:
            ax.scatter(
                point["vol"],
                point["return"],
                s=72,
                color=point["color"],
                edgecolors=chart_theme.BACKGROUND,
                linewidths=1.2,
                zorder=3,
            )
            ax.annotate(
                point["ticker"],
                xy=(point["vol"], point["return"]),
                xytext=(6, 4),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
                color=point["color"],
                annotation_clip=False,
            )

        ax.axhline(0.0, color=chart_theme.HAIRLINE, linewidth=1.0, zorder=1)
        if len(points) >= 3:
            ax.axvline(float(np.median(vols)), color=chart_theme.GRID, linewidth=0.9, zorder=1)

        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(y_lo, y_hi)
        ax.set_xlabel(x_label, fontsize=10, color=chart_theme.MUTED, labelpad=8)
        ax.set_ylabel(y_label, fontsize=10, color=chart_theme.MUTED, labelpad=8)
        ax.xaxis.set_major_formatter(
            plt.FuncFormatter(
                lambda val, _pos: f"{val:.0f}%".replace(".", "," if italian else ".")
            )
        )
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(
                lambda val, _pos: f"{val:+.0f}%".replace(".", "," if italian else ".")
            )
        )

        ax.set_title(
            title,
            loc="left",
            fontsize=14,
            fontweight="bold",
            color=chart_theme.INK,
            pad=14,
        )

        source = "Fonte: Yahoo Finance" if italian else "Source: Yahoo Finance"
        fig.text(
            0.01,
            0.01,
            f"Financial Researcher · {source}",
            fontsize=8,
            color=chart_theme.MUTED,
            ha="left",
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, format="png", bbox_inches="tight")
        plt.close(fig)

    return ChartArtifact(
        horizon="risk_return",
        caption=title,
        path=output_path,
        content_id=f"chart-risk-return-{output_path.stem}",
    )


def _breadth_caption(*, italian: bool, session: str) -> str:
    if session == "midday":
        return (
            "Ampiezza watchlist — positivi vs negativi (1D parziale e settimana)"
            if italian
            else "Watchlist breadth — advancing vs declining (partial 1D and week)"
        )
    if session == "pre_open":
        return (
            "Ampiezza watchlist — positivi vs negativi (settimana)"
            if italian
            else "Watchlist breadth — advancing vs declining (week)"
        )
    return (
        "Ampiezza watchlist — positivi vs negativi (giorno e settimana)"
        if italian
        else "Watchlist breadth — advancing vs declining (day and week)"
    )


def _count_performance_breadth(
    watchlist: list[dict[str, Any]],
    metric: str,
) -> dict[str, int]:
    """Count instruments with positive, negative, or flat performance for a horizon."""
    counts = {"up": 0, "down": 0, "flat": 0}
    for item in watchlist:
        perf = item.get("performance") or {}
        value = perf.get(metric)
        if value is None:
            continue
        numeric = float(value)
        if numeric > 0:
            counts["up"] += 1
        elif numeric < 0:
            counts["down"] += 1
        else:
            counts["flat"] += 1
    return counts


_BREADTH_FLAT = "#D1D5DB"


def _breadth_legend_labels(*, italian: bool) -> tuple[str, str, str]:
    if italian:
        return "Positivi", "Pari", "Negativi"
    return "Advancing", "Unchanged", "Declining"


def _render_breadth_donut(
    ax,
    counts: dict[str, int],
    *,
    metric_label: str,
    italian: bool,
) -> None:
    """Draw one donut for advancing / unchanged / declining counts."""
    pos_label, flat_label, neg_label = _breadth_legend_labels(italian=italian)
    segments: list[tuple[int, str]] = []
    for key, color in (
        ("up", chart_theme.POSITIVE),
        ("flat", _BREADTH_FLAT),
        ("down", chart_theme.NEGATIVE),
    ):
        if counts[key] > 0:
            segments.append((counts[key], color))

    if not segments:
        ax.axis("off")
        return

    sizes = [size for size, _ in segments]
    colors = [color for _, color in segments]
    total = sum(sizes)

    ax.pie(
        sizes,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={
            "width": 0.5,
            "edgecolor": chart_theme.BACKGROUND,
            "linewidth": 2.0,
        },
    )
    ax.text(
        0,
        0.06,
        str(total),
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold",
        color=chart_theme.INK,
    )
    instruments_word = "titoli" if italian else "names"
    ax.text(
        0,
        -0.14,
        instruments_word,
        ha="center",
        va="center",
        fontsize=9,
        color=chart_theme.MUTED,
    )
    ax.set_title(
        metric_label,
        fontsize=11,
        fontweight="600",
        color=chart_theme.INK,
        pad=10,
    )
    ax.set_aspect("equal")


def build_watchlist_breadth_chart(
    instruments: list[dict[str, Any]],
    *,
    session: str,
    output_path: Path,
    language: str,
    metrics: tuple[str, ...] | None = None,
) -> ChartArtifact | None:
    """Render donut charts of advancing/declining counts per session horizon."""
    italian = language.lower().startswith("ital")
    watchlist = _watchlist_instruments(instruments)
    if len(watchlist) < _MIN_BREADTH_INSTRUMENTS:
        return None

    chosen = metrics if metrics is not None else resolve_breadth_metrics(session)
    if not chosen:
        return None

    series: list[tuple[str, dict[str, int]]] = []
    for metric in chosen:
        counts = _count_performance_breadth(watchlist, metric)
        if counts["up"] + counts["down"] + counts["flat"] >= _MIN_BREADTH_INSTRUMENTS:
            series.append((metric, counts))

    if not series:
        return None

    title = _breadth_caption(italian=italian, session=session)
    pos_label, flat_label, neg_label = _breadth_legend_labels(italian=italian)

    with plt.rc_context(chart_theme.rcparams()):
        if len(series) == 1:
            fig, ax = plt.subplots(figsize=(5.4, 4.6))
            axes = [ax]
        else:
            fig, axes = plt.subplots(1, len(series), figsize=(8.6, 4.6))

        for ax, (metric, counts) in zip(np.atleast_1d(axes), series):
            metric_label = _BREADTH_METRIC_LABELS[metric][0 if italian else 1]
            if metric == "1d" and session == "midday":
                partial = " (parz.)" if italian else " (partial)"
                metric_label = f"{metric_label}{partial}"
            _render_breadth_donut(ax, counts, metric_label=metric_label, italian=italian)

        fig.suptitle(
            title,
            x=0.02,
            ha="left",
            fontsize=14,
            fontweight="bold",
            color=chart_theme.INK,
            y=0.98,
        )
        fig.legend(
            handles=[
                Patch(facecolor=chart_theme.POSITIVE, label=pos_label),
                Patch(facecolor=_BREADTH_FLAT, label=flat_label),
                Patch(facecolor=chart_theme.NEGATIVE, label=neg_label),
            ],
            loc="lower center",
            ncol=3,
            fontsize=9,
            frameon=False,
            labelcolor=chart_theme.MUTED,
            bbox_to_anchor=(0.5, -0.02),
        )

        source = "Fonte: Yahoo Finance" if italian else "Source: Yahoo Finance"
        fig.text(
            0.01,
            0.01,
            f"Financial Researcher · {source}",
            fontsize=8,
            color=chart_theme.MUTED,
            ha="left",
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, format="png", bbox_inches="tight")
        plt.close(fig)

    return ChartArtifact(
        horizon="breadth",
        caption=title,
        path=output_path,
        content_id=f"chart-breadth-{output_path.stem}",
    )


def _horizon_caption(horizon: str, *, italian: bool, session: str) -> str:
    if horizon == "1d":
        if session == "close":
            it, en = (
                "Andamento della seduta — base 100",
                "Session trend — indexed to 100",
            )
        elif session == "midday":
            it, en = (
                "Andamento intraday (parziale) — base 100",
                "Intraday trend (partial) — indexed to 100",
            )
        else:
            it, en = (
                "Andamento intraday — base 100",
                "Intraday trend — indexed to 100",
            )
        return it if italian else en

    captions = {
        "1w": (
            "Andamento settimanale — base 100",
            "Weekly trend — indexed to 100",
        ),
        "1m": (
            "Andamento mensile — base 100",
            "1-month trend — indexed to 100",
        ),
        "ytd": (
            "Andamento da inizio anno — base 100",
            "Year-to-date trend — indexed to 100",
        ),
        "1y": (
            "Andamento su 12 mesi — base 100",
            "12-month trend — indexed to 100",
        ),
    }
    it, en = captions.get(horizon, (horizon, horizon))
    return it if italian else en


def _parse_dates(raw_dates: list[str]) -> list[datetime]:
    parsed: list[datetime] = []
    for value in raw_dates:
        try:
            parsed.append(datetime.fromisoformat(str(value)[:10]))
        except (ValueError, TypeError):
            parsed.append(datetime.min)
    return parsed


def _parse_timestamps(raw_timestamps: list[str]) -> list[datetime]:
    parsed: list[datetime] = []
    for value in raw_timestamps:
        text = str(value).strip()
        try:
            if len(text) == 10:
                parsed.append(datetime.fromisoformat(text))
            else:
                parsed.append(datetime.fromisoformat(text[:19]))
        except (ValueError, TypeError):
            parsed.append(datetime.min)
    return parsed


def _slice_daily_series(
    dates: list[datetime],
    closes: list[float],
    horizon: str,
) -> tuple[list[datetime], list[float]]:
    sessions = _HORIZON_SESSIONS.get(horizon)
    if sessions is None:
        year = date.today().year
        pairs = [(d, c) for d, c in zip(dates, closes) if d.year == year]
        if pairs:
            return [p[0] for p in pairs], [p[1] for p in pairs]
        return dates, closes
    if len(closes) <= sessions:
        return dates, closes
    return dates[-(sessions + 1) :], closes[-(sessions + 1) :]


def _indexed(closes: list[float]) -> list[float]:
    base = next((c for c in closes if c), None)
    if not base:
        return [100.0 for _ in closes]
    return [round(c / base * 100, 4) for c in closes]


def _extract_daily_series(
    instrument: dict[str, Any],
) -> tuple[list[datetime], list[float]] | None:
    history = instrument.get("history") or {}
    raw_dates = history.get("dates") or []
    raw_closes = history.get("closes") or []
    if not raw_dates or not raw_closes or len(raw_dates) != len(raw_closes):
        return None
    closes = [float(c) for c in raw_closes if c is not None]
    if len(closes) != len(raw_closes):
        return None
    return _parse_dates(raw_dates), closes


def _extract_intraday_series(
    instrument: dict[str, Any],
) -> tuple[list[datetime], list[float]] | None:
    intraday = instrument.get("intraday") or {}
    raw_ts = intraday.get("timestamps") or []
    raw_closes = intraday.get("closes") or []
    if not raw_ts or not raw_closes or len(raw_ts) != len(raw_closes):
        return None
    closes = [float(c) for c in raw_closes if c is not None]
    if len(closes) != len(raw_closes):
        return None
    return _parse_timestamps(raw_ts), closes


def _extract_chart_series(
    instrument: dict[str, Any],
    horizon: str,
) -> tuple[list[datetime], list[float]] | None:
    if horizon == "1d":
        series = _extract_intraday_series(instrument)
        if series is None:
            return None
        dates, closes = series
        if len(closes) < _MIN_INTRADAY_POINTS:
            return None
        return dates, closes

    series = _extract_daily_series(instrument)
    if series is None:
        return None
    dates, closes = _slice_daily_series(series[0], series[1], horizon)
    if len(closes) < _MIN_DAILY_POINTS:
        return None
    return dates, closes


def _fmt_delta(pct: float, *, italian: bool) -> str:
    sign = "+" if pct >= 0 else "−"
    body = f"{abs(pct):.1f}%".replace(".", "," if italian else ".")
    return f"{sign}{body}"


def _place_end_labels(ax, entries: list[dict[str, Any]], *, italian: bool) -> None:
    """Draw ticker + final delta at the right edge, nudged to avoid overlap."""
    if not entries:
        return
    ordered = sorted(entries, key=lambda e: e["y"])
    y_min, y_max = ax.get_ylim()
    min_gap = (y_max - y_min) * 0.05
    last_y: float | None = None
    for entry in ordered:
        label_y = entry["y"]
        if last_y is not None and label_y - last_y < min_gap:
            label_y = last_y + min_gap
        last_y = label_y
        delta = _fmt_delta(entry["y"] - 100.0, italian=italian)
        ax.annotate(
            f"{entry['ticker']}  {delta}",
            xy=(entry["x"], entry["y"]),
            xytext=(8, label_y),
            textcoords=("offset points", "data"),
            va="center",
            ha="left",
            fontsize=9,
            fontweight="bold",
            color=entry["color"],
            annotation_clip=False,
        )


def _configure_time_axis(ax, *, horizon: str) -> None:
    if horizon == "1d":
        locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    else:
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))


def build_indexed_chart(
    instruments: list[dict[str, Any]],
    *,
    horizon: str,
    session: str,
    output_path: Path,
    language: str,
    title: str,
) -> ChartArtifact | None:
    """Render one indexed multi-line chart. Returns None when data is insufficient."""
    italian = language.lower().startswith("ital")

    plottable: list[dict[str, Any]] = []
    for index, instrument in enumerate(instruments):
        series = _extract_chart_series(instrument, horizon)
        if series is None:
            continue
        dates, closes = series
        values = _indexed(closes)
        plottable.append(
            {
                "ticker": instrument.get("ticker", "?"),
                "dates": dates,
                "values": values,
                "color": chart_theme.series_color(index),
                "x": dates[-1],
                "y": values[-1],
            }
        )

    if not plottable:
        return None

    with plt.rc_context(chart_theme.rcparams()):
        fig, ax = plt.subplots(figsize=(9.2, 4.6))
        chart_theme.style_axes(ax)

        ranked = sorted(plottable, key=lambda e: e["y"], reverse=True)
        for entry in ranked:
            is_leader = entry is ranked[0]
            ax.plot(
                entry["dates"],
                entry["values"],
                color=entry["color"],
                linewidth=2.4 if is_leader else 1.7,
                solid_capstyle="round",
                solid_joinstyle="round",
                alpha=1.0 if is_leader else 0.9,
                zorder=3 if is_leader else 2,
            )
            if is_leader:
                ax.fill_between(
                    entry["dates"],
                    entry["values"],
                    100.0,
                    color=entry["color"],
                    alpha=0.06,
                    zorder=1,
                )

        ax.axhline(100.0, color=chart_theme.HAIRLINE, linewidth=1.0, zorder=1)
        _configure_time_axis(ax, horizon=horizon)

        ax.margins(x=0.02)
        ax.set_xlim(right=ax.get_xlim()[1] + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.18)

        ax.set_title(
            title,
            loc="left",
            fontsize=14,
            fontweight="bold",
            color=chart_theme.INK,
            pad=16,
        )

        _place_end_labels(ax, plottable, italian=italian)

        source = "Fonte: Yahoo Finance" if italian else "Source: Yahoo Finance"
        fig.text(
            0.01,
            -0.02,
            f"Financial Researcher · {source}",
            fontsize=8,
            color=chart_theme.MUTED,
            ha="left",
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, format="png")
        plt.close(fig)

    return ChartArtifact(
        horizon=horizon,
        caption=_horizon_caption(horizon, italian=italian, session=session),
        path=output_path,
        content_id=f"chart-{horizon}-{output_path.stem}",
    )


def generate_briefing_charts(
    instruments: list[dict[str, Any]],
    *,
    session: str,
    language: str,
    slug: str,
    out_dir: Path,
    horizons: tuple[str, ...] | None = None,
) -> list[ChartArtifact]:
    """Render session-appropriate charts for a briefing run."""
    italian = language.lower().startswith("ital")
    artifacts: list[ChartArtifact] = []

    heatmap_path = out_dir / f"{slug}_heatmap.png"
    heatmap = build_performance_heatmap(
        instruments,
        session=session,
        output_path=heatmap_path,
        language=language,
    )
    if heatmap is not None:
        artifacts.append(heatmap)

    scatter_path = out_dir / f"{slug}_risk_return.png"
    scatter = build_risk_return_scatter(
        instruments,
        session=session,
        output_path=scatter_path,
        language=language,
    )
    if scatter is not None:
        artifacts.append(scatter)

    breadth_path = out_dir / f"{slug}_breadth.png"
    breadth = build_watchlist_breadth_chart(
        instruments,
        session=session,
        output_path=breadth_path,
        language=language,
    )
    if breadth is not None:
        artifacts.append(breadth)

    chosen = horizons if horizons is not None else resolve_chart_horizons(session)
    for horizon in chosen:
        caption = _horizon_caption(horizon, italian=italian, session=session)
        output_path = out_dir / f"{slug}_{horizon}.png"
        artifact = build_indexed_chart(
            instruments,
            horizon=horizon,
            session=session,
            output_path=output_path,
            language=language,
            title=caption,
        )
        if artifact is not None:
            artifacts.append(artifact)
    return artifacts


def build_charts_markdown(
    artifacts: list[ChartArtifact],
    *,
    language: str,
    base_dir: Path | None = None,
) -> str:
    """Markdown block of chart images, referenced by path relative to base_dir."""
    if not artifacts:
        return ""
    italian = language.lower().startswith("ital")
    heading = "Andamento Grafico" if italian else "Performance Charts"
    lines = [f"### {heading}", ""]
    for artifact in artifacts:
        if base_dir is not None:
            try:
                src = artifact.path.relative_to(base_dir).as_posix()
            except ValueError:
                src = artifact.path.as_posix()
        else:
            src = artifact.path.as_posix()
        lines.append(f"![{artifact.caption}]({src})")
        lines.append("")
    return "\n".join(lines).strip()
