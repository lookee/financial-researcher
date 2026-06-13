"""Generate elegant, deterministic performance charts for briefings.

Charts are rendered in pure Python (matplotlib, Agg backend) from the daily
close series already fetched by the market pipeline. They never touch the LLMs:
the crew receives no price series and no images — charts are produced after the
crew has run and injected into the final markdown / email.

The hero visual is a multi-line chart indexed to 100 at the start of the
horizon, so instruments of very different prices can be compared on one scale.
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

from financial_researcher.services import chart_theme

# Horizon -> trailing sessions (None means "year-to-date", sliced by date).
_HORIZON_SESSIONS: dict[str, int | None] = {
    "1w": 5,
    "1m": 21,
    "ytd": None,
    "1y": 252,
}

# Default horizons rendered per briefing (best representations from daily closes).
_DEFAULT_HORIZONS: tuple[str, ...] = ("1w", "1y")

_MIN_POINTS = 3


@dataclass(frozen=True)
class ChartArtifact:
    """A rendered chart ready to embed in markdown and email."""

    horizon: str
    caption: str
    path: Path
    content_id: str


def _horizon_caption(horizon: str, *, italian: bool) -> str:
    captions = {
        "1w": ("Andamento settimanale — base 100", "Weekly trend — indexed to 100"),
        "1m": ("Andamento mensile — base 100", "1-month trend — indexed to 100"),
        "ytd": ("Andamento da inizio anno — base 100", "Year-to-date trend — indexed to 100"),
        "1y": ("Andamento su 12 mesi — base 100", "12-month trend — indexed to 100"),
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


def _slice_series(
    dates: list[datetime],
    closes: list[float],
    horizon: str,
) -> tuple[list[datetime], list[float]]:
    sessions = _HORIZON_SESSIONS.get(horizon, None)
    if sessions is None:  # year-to-date
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


def _extract_series(instrument: dict[str, Any]) -> tuple[list[datetime], list[float]] | None:
    history = instrument.get("history") or {}
    raw_dates = history.get("dates") or []
    raw_closes = history.get("closes") or []
    if not raw_dates or not raw_closes or len(raw_dates) != len(raw_closes):
        return None
    closes = [float(c) for c in raw_closes if c is not None]
    if len(closes) != len(raw_closes):
        return None
    return _parse_dates(raw_dates), closes


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


def build_indexed_chart(
    instruments: list[dict[str, Any]],
    *,
    horizon: str,
    output_path: Path,
    language: str,
    title: str,
) -> ChartArtifact | None:
    """Render one indexed multi-line chart. Returns None when data is insufficient."""
    italian = language.lower().startswith("ital")

    plottable: list[dict[str, Any]] = []
    for index, instrument in enumerate(instruments):
        series = _extract_series(instrument)
        if series is None:
            continue
        dates, closes = _slice_series(series[0], series[1], horizon)
        if len(closes) < _MIN_POINTS:
            continue
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

        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

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
        caption=_horizon_caption(horizon, italian=italian),
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
    horizons: tuple[str, ...] = _DEFAULT_HORIZONS,
) -> list[ChartArtifact]:
    """Render the set of charts for a briefing run. Empty list when no data."""
    italian = language.lower().startswith("ital")
    artifacts: list[ChartArtifact] = []
    for horizon in horizons:
        caption = _horizon_caption(horizon, italian=italian)
        output_path = out_dir / f"{slug}_{horizon}.png"
        artifact = build_indexed_chart(
            instruments,
            horizon=horizon,
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
