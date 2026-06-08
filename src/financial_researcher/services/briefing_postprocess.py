"""Deterministic post-processing for generated watchlist briefings."""

from __future__ import annotations

import json
import re
from typing import Any

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
CITATION_RE = re.compile(r"\[(\d+)\]")
NUMBERED_REF_RE = re.compile(r"^(\d+)\.\s+(.+)$", re.MULTILINE)

PERFORMANCE_SECTION_TITLES = {
    "prestazioni della watchlist",
    "watchlist performance snapshot",
    "scatto della performance della watchlist",
}

REFERENCES_SECTION_TITLES = {
    "riferimenti",
    "references",
}

DISCLAIMER_SECTION_TITLES = {
    "disclaimer",
}


def _normalize_title(title: str) -> str:
    return title.strip().lower()


def _heading_level(marker: str) -> int:
    return len(marker)


def _find_sections(content: str) -> list[tuple[int, int, int, str]]:
    """Return (start, end, level, title) for each markdown heading block."""
    matches = list(HEADING_RE.finditer(content))
    sections: list[tuple[int, int, int, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        level = _heading_level(match.group(1))
        title = match.group(2)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        sections.append((start, end, level, title))
    return sections


def _replace_section_body(
    content: str,
    *,
    title_keys: set[str],
    new_body: str,
) -> str:
    """Replace a section body, keeping its heading line."""
    sections = _find_sections(content)
    for start, end, level, title in sections:
        if _normalize_title(title) not in title_keys:
            continue
        heading_line_end = content.find("\n", start)
        if heading_line_end == -1:
            heading_line_end = end
        heading = content[start:heading_line_end]
        next_start = end
        for other_start, other_end, other_level, _ in sections:
            if other_start <= start:
                continue
            if other_level <= level:
                next_start = other_start
                break
        replacement = f"{heading}\n\n{new_body.strip()}\n\n"
        return content[:start] + replacement + content[next_start:].lstrip("\n")
    return content


def _split_before_section(content: str, title_keys: set[str]) -> tuple[str, str | None, str]:
    """Split content into (before, section_with_heading, after)."""
    sections = _find_sections(content)
    for start, end, level, title in sections:
        if _normalize_title(title) not in title_keys:
            continue
        next_start = len(content)
        for other_start, _, other_level, _ in sections:
            if other_start <= start:
                continue
            if other_level <= level:
                next_start = other_start
                break
        return content[:start], content[start:next_start], content[next_start:]
    return content, None, ""


def build_market_data_references(
    instruments: list[dict[str, Any]],
    *,
    date_str: str,
) -> list[str]:
    lines: list[str] = []
    for item in instruments:
        citation = item["citation"]
        ticker = item["ticker"]
        name = item["name"]
        url = item.get("source_url") or f"https://finance.yahoo.com/quote/{ticker}"
        lines.append(
            f"{citation}. Yahoo Finance — {ticker} ({name}) — {date_str} — {url}"
        )
    return lines


def build_performance_highlights(
    instruments: list[dict[str, Any]],
    *,
    language: str = "English",
) -> str:
    """One-line leader/laggard summary by 1D performance."""
    ranked = [
        (item, item.get("performance", {}).get("1d"))
        for item in instruments
        if item.get("performance", {}).get("1d") is not None
    ]
    if len(ranked) < 2:
        return ""

    ranked.sort(key=lambda pair: pair[1], reverse=True)
    leader_ticker = ranked[0][0]["ticker"]
    leader_pct = ranked[0][1]
    laggard_ticker = ranked[-1][0]["ticker"]
    laggard_pct = ranked[-1][1]

    def fmt_pct(value: float) -> str:
        return f"{value:,.2f}%"

    if language.lower().startswith("ital"):
        return (
            f"**Leader 1D:** {leader_ticker} ({fmt_pct(leader_pct)}) · "
            f"**Laggard 1D:** {laggard_ticker} ({fmt_pct(laggard_pct)})"
        )
    return (
        f"**1D leader:** {leader_ticker} ({fmt_pct(leader_pct)}) · "
        f"**1D laggard:** {laggard_ticker} ({fmt_pct(laggard_pct)})"
    )


def _parse_research_references(section: str) -> list[str]:
    """Extract non-Yahoo reference lines from a references section."""
    research: list[tuple[int, str]] = []
    for match in NUMBERED_REF_RE.finditer(section):
        number = int(match.group(1))
        text = match.group(2).strip()
        if "yahoo finance" in text.lower():
            continue
        research.append((number, text))
    research.sort(key=lambda item: item[0])
    return [text for _, text in research]


def _merge_references_section(
    content: str,
    *,
    yahoo_refs: list[str],
    instrument_count: int,
    language: str,
) -> str:
    before, refs_block, after = _split_before_section(content, REFERENCES_SECTION_TITLES)
    if refs_block is None:
        heading = "### Riferimenti" if language.lower().startswith("ital") else "### References"
        research_lines = []
        tail = after
    else:
        heading_match = HEADING_RE.search(refs_block)
        heading = heading_match.group(0) if heading_match else "### References"
        disclaimer_block = ""
        tail = after
        refs_body = refs_block
        for title in DISCLAIMER_SECTION_TITLES:
            disc_before, disc_section, disc_after = _split_before_section(refs_body, {title})
            if disc_section is not None:
                refs_body = disc_before
                disclaimer_block = disc_section + disc_after
                tail = disclaimer_block + tail
                break
        research_lines = _parse_research_references(refs_body)

    renumbered = [
        f"{instrument_count + index + 1}. {line}"
        for index, line in enumerate(research_lines)
    ]
    all_refs = yahoo_refs + renumbered
    refs_text = heading + "\n\n" + "\n".join(all_refs)
    if tail.strip():
        return before.rstrip() + "\n\n" + refs_text + "\n\n" + tail.lstrip("\n")
    return before.rstrip() + "\n\n" + refs_text + "\n"


def validate_citations(content: str, *, reference_count: int) -> list[str]:
    """Return human-readable warnings for citation/reference mismatches."""
    warnings: list[str] = []
    used = {int(value) for value in CITATION_RE.findall(content)}
    if not used:
        warnings.append("No [N] citations found in briefing body.")
        return warnings

    max_used = max(used)
    if max_used > reference_count:
        warnings.append(
            f"Citations up to [{max_used}] but only {reference_count} references listed."
        )

    missing = sorted(number for number in range(1, reference_count + 1) if number not in used)
    if missing and len(missing) <= 6:
        warnings.append(f"Market-data citations never used in body: {missing}")

    return warnings


def postprocess_briefing(content: str, inputs: dict[str, str]) -> tuple[str, list[str]]:
    """Apply deterministic fixes to a generated briefing markdown document."""
    context = json.loads(inputs["watchlist_context"])
    instruments: list[dict[str, Any]] = context["instruments"]
    language = inputs.get("language", "English")
    date_str = inputs.get("current_date", context.get("current_date", ""))
    instrument_count = len(instruments)

    performance_table = inputs.get("watchlist_performance_table", "")
    highlights = build_performance_highlights(instruments, language=language)
    performance_body = performance_table
    if highlights:
        performance_body = f"{highlights}\n\n{performance_table}"

    updated = _replace_section_body(
        content,
        title_keys=PERFORMANCE_SECTION_TITLES,
        new_body=performance_body,
    )
    if updated == content and performance_table:
        # Section missing — insert after executive summary if possible.
        exec_titles = {"sommario esecutivo", "executive summary"}
        sections = _find_sections(content)
        for start, end, level, title in sections:
            if _normalize_title(title) not in exec_titles:
                continue
            perf_heading = (
                "### Prestazioni della Watchlist"
                if language.lower().startswith("ital")
                else "### Watchlist Performance Snapshot"
            )
            insert = f"\n\n{perf_heading}\n\n{performance_body.strip()}\n\n"
            updated = content[:end].rstrip() + insert + content[end:].lstrip("\n")
            break

    yahoo_refs = build_market_data_references(instruments, date_str=date_str)
    updated = _merge_references_section(
        updated,
        yahoo_refs=yahoo_refs,
        instrument_count=instrument_count,
        language=language,
    )

    body, refs_block, _ = _split_before_section(updated, REFERENCES_SECTION_TITLES)
    reference_count = len(NUMBERED_REF_RE.findall(refs_block or ""))
    warnings = validate_citations(body or updated, reference_count=reference_count)
    return updated, warnings
