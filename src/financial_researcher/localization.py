"""English briefing section headings and UI labels."""

from __future__ import annotations

BRIEFING_SECTION_ORDER: tuple[str, ...] = (
    "executive_summary",
    "performance",
    "drivers",
    "outlook",
    "calendar",
    "themes",
    "risks",
    "references",
    "disclaimer",
)

SECTION_HEADINGS: dict[str, str] = {
    "executive_summary": "Executive Summary",
    "performance": "Watchlist Performance Snapshot",
    "drivers": "What's Driving the Moves",
    "outlook": "Medium-Term Outlook",
    "calendar": "Event Calendar",
    "themes": "Correlated Themes",
    "risks": "Risks & Watchpoints",
    "references": "References",
    "disclaimer": "Disclaimer",
}

# Legacy / variant titles (lowercase) → section key for post-process matching.
SECTION_ALIASES: dict[str, str] = {
    "whats driving the moves": "drivers",
    "sommario esecutivo": "executive_summary",
    "snapshot della performance watchlist": "performance",
    "scatto della performance della watchlist": "performance",
    "prestazioni della watchlist": "performance",
    "performance": "performance",
    "performance snapshot": "performance",
    "cosa guida i movimenti": "drivers",
    "medium-term outlook": "outlook",
    "prospettive a medio termine": "outlook",
    "outlook a medio termine": "outlook",
    "event calendar": "calendar",
    "calendario eventi": "calendar",
    "calendario degli eventi": "calendar",
    "correlated themes": "themes",
    "temi correlati": "themes",
    "risks and watchpoints": "risks",
    "rischi e punti di attenzione": "risks",
    "riferimenti": "references",
    "note legali": "disclaimer",
}

CHART_LABELS: dict[str, str] = {
    "performance_charts": "Performance Charts",
}

RUN_METADATA_LABELS: dict[str, str] = {
    "heading": "Run metadata",
    "profile": "Model profile",
    "duration": "Processing time",
    "requests": "LLM requests",
    "tokens": "Tokens (prompt / completion / total)",
    "agents_heading": "Models by agent",
    "agent_col": "Agent",
    "model_col": "Model (configured → resolved)",
    "openrouter_savings": "OpenRouter savings (1–10)",
}

AGENT_LABELS: dict[str, str] = {
    "market": "Market analyst",
    "news": "News analyst",
    "outlook": "Outlook analyst",
    "calendar": "Calendar analyst",
    "chief": "Chief strategist",
}


def is_italian_language(language: str) -> bool:
    """True when briefing prose should use Italian (numbers, tables, etc.)."""
    return language.strip().lower().startswith("ital")


def label(domain: str, key: str) -> str:
    """Return an English UI string."""
    blocks = {
        "sections": SECTION_HEADINGS,
        "charts": CHART_LABELS,
        "run_metadata": RUN_METADATA_LABELS,
        "agents": AGENT_LABELS,
    }
    block = blocks.get(domain) or {}
    value = block.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return key


def briefing_section_order() -> list[str]:
    return list(BRIEFING_SECTION_ORDER)


def section_heading(section_key: str, *, language: str | None = None) -> str:
    """English ## heading for a briefing section (language ignored)."""
    _ = language
    return label("sections", section_key)


def localized_section_heading(section_key: str, language: str) -> str:
    """Backward-compatible alias."""
    return section_heading(section_key, language=language)


def english_section_headings() -> dict[str, str]:
    return {key: SECTION_HEADINGS[key] for key in BRIEFING_SECTION_ORDER}


def section_alias_map() -> dict[str, str]:
    """Normalized lowercase title → section key."""
    aliases = dict(SECTION_ALIASES)
    for key, title in SECTION_HEADINGS.items():
        aliases[title.lower()] = key
    return aliases


def section_title_variants(section_key: str) -> set[str]:
    """All known lowercase titles for one section."""
    keys = {section_heading(section_key).lower()}
    for alias, key in section_alias_map().items():
        if key == section_key:
            keys.add(alias)
    return keys


def run_metadata_copy(*, language: str | None = None) -> dict[str, str]:
    _ = language
    return dict(RUN_METADATA_LABELS)


def agent_label(agent_key: str, *, language: str | None = None) -> str:
    _ = language
    return label("agents", agent_key)


def agent_labels(*, language: str | None = None) -> dict[str, str]:
    _ = language
    return dict(AGENT_LABELS)
