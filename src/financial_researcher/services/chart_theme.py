"""Centralized visual theme for briefing charts.

A restrained, editorial palette on a pure-white canvas (#FFFFFF) to match the
email body. The goal is an elegant, institutional look: thin spines, hairline
horizontal grid, generous whitespace, and end-of-line value labels instead of a
crowded legend.
"""

from __future__ import annotations

from typing import Any

# Pure white to align with the email background.
BACKGROUND = "#FFFFFF"

# Editorial ink tones.
INK = "#1A1A1A"
MUTED = "#6B7280"
HAIRLINE = "#E5E7EB"
GRID = "#EEF0F2"

# Curated, high-contrast yet refined series palette (color-blind friendly-ish).
SERIES_PALETTE: tuple[str, ...] = (
    "#2563EB",  # cobalt
    "#D97706",  # amber
    "#059669",  # emerald
    "#DC2626",  # vermillion
    "#7C3AED",  # violet
    "#0891B2",  # teal
    "#DB2777",  # magenta
    "#65A30D",  # olive
    "#475569",  # slate
    "#B45309",  # bronze
)

POSITIVE = "#059669"
NEGATIVE = "#DC2626"

FONT_STACK: tuple[str, ...] = (
    "Inter",
    "Helvetica Neue",
    "Helvetica",
    "Arial",
    "DejaVu Sans",
    "sans-serif",
)


def series_color(index: int) -> str:
    """Stable color for the n-th series, cycling through the palette."""
    return SERIES_PALETTE[index % len(SERIES_PALETTE)]


def rcparams() -> dict[str, Any]:
    """Matplotlib rcParams that encode the house style."""
    return {
        "figure.facecolor": BACKGROUND,
        "savefig.facecolor": BACKGROUND,
        "axes.facecolor": BACKGROUND,
        "font.family": "sans-serif",
        "font.sans-serif": list(FONT_STACK),
        "font.size": 11,
        "text.color": INK,
        "axes.edgecolor": HAIRLINE,
        "axes.labelcolor": MUTED,
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "grid.linewidth": 0.9,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.frameon": False,
        "figure.dpi": 110,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.25,
    }


def style_axes(ax) -> None:
    """Apply the editorial despine + hairline grid to an Axes."""
    ax.set_facecolor(BACKGROUND)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(HAIRLINE)
    ax.tick_params(length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.9)
    ax.set_axisbelow(True)
