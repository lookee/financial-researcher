"""Deterministic post-processing for generated watchlist briefings."""

from __future__ import annotations

import json
import re
from typing import Any

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
CITATION_RE = re.compile(r"\[(\d+)\]")
NUMBERED_REF_RE = re.compile(r"^(\d+)\.\s+(.+)$", re.MULTILINE)

from financial_researcher.services.watchlist_context import instrument_label

# Canonical English headings (prompt template). Post-process matches EN + IT aliases.
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

SECTION_ALIASES: dict[str, str] = {
    "executive summary": "executive_summary",
    "sommario esecutivo": "executive_summary",
    "watchlist performance snapshot": "performance",
    "scatto della performance della watchlist": "performance",
    "prestazioni della watchlist": "performance",
    "what's driving the moves": "drivers",
    "whats driving the moves": "drivers",
    "cosa guida i movimenti": "drivers",
    "medium-term outlook": "outlook",
    "outlook a medio termine": "outlook",
    "prospettive a medio termine": "outlook",
    "event calendar": "calendar",
    "calendario degli eventi": "calendar",
    "correlated themes": "themes",
    "temi correlati": "themes",
    "risks & watchpoints": "risks",
    "risks and watchpoints": "risks",
    "rischi e punti di attenzione": "risks",
    "references": "references",
    "riferimenti": "references",
    "disclaimer": "disclaimer",
    "note legali": "disclaimer",
}


def section_title(section_key: str) -> str:
    return SECTION_HEADINGS[section_key]


def _section_title_keys(section_key: str) -> set[str]:
    keys = {SECTION_HEADINGS[section_key].lower()}
    for alias, key in SECTION_ALIASES.items():
        if key == section_key:
            keys.add(alias)
    return keys


def performance_section_titles() -> set[str]:
    return _section_title_keys("performance")


def references_section_titles() -> set[str]:
    return _section_title_keys("references")


def disclaimer_section_titles() -> set[str]:
    return {"disclaimer", "note legali"}


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
    leader = ranked[0][0]
    laggard = ranked[-1][0]
    leader_pct = ranked[0][1]
    laggard_pct = ranked[-1][1]

    def fmt_pct(value: float) -> str:
        return f"{value:,.2f}%"

    def _label(item: dict[str, Any]) -> str:
        return instrument_label(item)

    if language.lower().startswith("ital"):
        return (
            f"**Leader 1D:** {_label(leader)} ({fmt_pct(leader_pct)}) · "
            f"**Laggard 1D:** {_label(laggard)} ({fmt_pct(laggard_pct)})"
        )
    return (
        f"**1D leader:** {_label(leader)} ({fmt_pct(leader_pct)}) · "
        f"**1D laggard:** {_label(laggard)} ({fmt_pct(laggard_pct)})"
    )


def _parse_research_references(section: str) -> dict[int, str]:
    """Extract non-Yahoo reference lines keyed by citation number."""
    research: dict[int, str] = {}
    for match in NUMBERED_REF_RE.finditer(section):
        number = int(match.group(1))
        text = match.group(2).strip()
        if "yahoo finance" in text.lower():
            continue
        research[number] = text
    return research


def _format_seed_reference(entry: dict[str, Any]) -> str:
    return (
        f"{entry['source']} — {entry['title']} — {entry.get('date', 'n/a')} — "
        f"{entry['url']}"
    )


def _load_seed_references(inputs: dict[str, str]) -> dict[int, str]:
    raw = inputs.get("research_reference_seed_json", "").strip()
    if not raw:
        return {}
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return {
        int(entry["citation"]): _format_seed_reference(entry)
        for entry in entries
        if entry.get("citation") and entry.get("url")
    }


def _merge_references_section(
    content: str,
    *,
    yahoo_refs: list[str],
    seed_refs: dict[int, str],
    body: str,
    instrument_count: int,
) -> str:
    before, refs_block, after = _split_before_section(
        content, references_section_titles()
    )
    if refs_block is None:
        heading = f"## {section_title('references')}"
        research_lines: dict[int, str] = {}
        tail = after
    else:
        heading_match = HEADING_RE.search(refs_block)
        heading = heading_match.group(0) if heading_match else f"## {section_title('references')}"
        disclaimer_block = ""
        tail = after
        refs_body = refs_block
        for title in disclaimer_section_titles():
            disc_before, disc_section, disc_after = _split_before_section(refs_body, {title})
            if disc_section is not None:
                refs_body = disc_before
                disclaimer_block = disc_section + disc_after
                tail = disclaimer_block + tail
                break
        research_lines = _parse_research_references(refs_body if refs_block else "")

    merged = dict(seed_refs)
    merged.update(research_lines)

    cited = {
        int(value)
        for value in CITATION_RE.findall(body)
        if int(value) > instrument_count
    }
    ref_numbers = sorted(set(merged.keys()) | cited)

    research_formatted = [
        f"{number}. {merged[number]}"
        for number in ref_numbers
        if number in merged
    ]
    all_refs = yahoo_refs + research_formatted
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


def validate_material_news_prominence(content: str, inputs: dict[str, str]) -> list[str]:
    """Warn when HIGH material news may have been diluted or replaced in narrative."""
    material = inputs.get("watchlist_material_news", "")
    if "Impatto **HIGH**" not in material and "Impact **HIGH**" not in material:
        return []

    warnings: list[str] = []
    lowered = content.lower()
    vague_markers = ("speculaz", "incertezze nel settore", "competizione nel settore")
    if any(marker in lowered for marker in vague_markers) and (
        "notizia dominante" in material.lower() or "dominant watchlist story" in material.lower()
    ):
        warnings.append(
            "Prefetch flagged HIGH issuer news as the dominant watchlist story, but the "
            "briefing uses vague sector/speculation language — verify headline facts and [N] "
            "appear in the Executive Summary and Drivers."
        )

    raw_seed = inputs.get("research_reference_seed_json", "").strip()
    if raw_seed:
        try:
            seed = json.loads(raw_seed)
        except json.JSONDecodeError:
            seed = []
        for entry in seed:
            url = (entry.get("url") or "").lower()
            title = (entry.get("title") or "").lower()
            ticker = entry.get("ticker", "")
            if "borsaitaliana.it" not in url or ticker.upper() != "ISP.MI":
                continue
            if title and title[:40] not in lowered and "bancaditalia" in lowered:
                warnings.append(
                    "Prefetch top ISP headline is from Borsa Italiana but briefing emphasises "
                    "Banca d'Italia — verify the correct issuer story is reported."
                )
                break

    return warnings


def postprocess_briefing(content: str, inputs: dict[str, str]) -> tuple[str, list[str]]:
    """Apply deterministic fixes to a generated briefing markdown document."""
    updated = content

    context = json.loads(inputs["watchlist_context"])
    instruments: list[dict[str, Any]] = context["instruments"]
    language = inputs.get("language", context.get("language", "English"))
    date_str = inputs.get("current_date", context.get("current_date", ""))
    instrument_count = len(instruments)

    performance_table = inputs.get("watchlist_performance_table", "")
    highlights = build_performance_highlights(instruments, language=language)
    performance_body = performance_table
    if highlights:
        performance_body = f"{highlights}\n\n{performance_table}"

    before_perf = updated
    updated = _replace_section_body(
        updated,
        title_keys=performance_section_titles(),
        new_body=performance_body,
    )
    if updated == before_perf and performance_table:
        exec_keys = _section_title_keys("executive_summary")
        sections = _find_sections(updated)
        for start, end, level, title in sections:
            if _normalize_title(title) not in exec_keys:
                continue
            perf_heading = f"## {section_title('performance')}"
            insert = f"\n\n{perf_heading}\n\n{performance_body.strip()}\n\n"
            updated = updated[:end].rstrip() + insert + updated[end:].lstrip("\n")
            break

    yahoo_refs = build_market_data_references(instruments, date_str=date_str)
    seed_refs = _load_seed_references(inputs)
    body_before_refs, _, _ = _split_before_section(updated, references_section_titles())
    updated = _merge_references_section(
        updated,
        yahoo_refs=yahoo_refs,
        seed_refs=seed_refs,
        body=body_before_refs or updated,
        instrument_count=instrument_count,
    )

    body, refs_block, _ = _split_before_section(updated, references_section_titles())
    reference_count = len(NUMBERED_REF_RE.findall(refs_block or ""))
    warnings = validate_citations(body or updated, reference_count=reference_count)
    warnings.extend(validate_material_news_prominence(updated, inputs))
    return updated, warnings
