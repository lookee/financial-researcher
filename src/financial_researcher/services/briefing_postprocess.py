"""Deterministic post-processing for generated watchlist briefings."""

from __future__ import annotations

import json
import re
from typing import Any

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.MULTILINE)
CITATION_RE = re.compile(r"\[(\d+)\]")
NUMBERED_REF_RE = re.compile(r"^(\d+)\.\s+(.+)$", re.MULTILINE)
MATERIAL_IMPACT_RE = re.compile(
    r"^### (.+?) — Impact \*\*(HIGH|MEDIUM|LOW|NONE)\*\*",
    re.MULTILINE,
)
TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$", re.MULTILINE)

from financial_researcher.services.news_ranking import OFFICIAL_DOMAINS
from financial_researcher.services.watchlist_context import (
    BRIEFING_SECTION_HEADINGS_EN,
    BRIEFING_SECTION_HEADINGS_IT,
    instrument_label,
    is_italian_language,
    localized_section_heading,
)

CANONICAL_CALENDAR_HEADERS = [
    "Date (YYYY-MM-DD)",
    "Event",
    "Affected tickers/themes",
    "Impact",
    "[N]",
]

CALENDAR_HEADER_ALIASES: dict[str, int] = {
    "date": 0,
    "date (yyyy-mm-dd)": 0,
    "data": 0,
    "data (yyyy-mm-dd)": 0,
    "event": 1,
    "evento": 1,
    "affected tickers/themes": 2,
    "affected tickers / themes": 2,
    "affected instruments / themes": 2,
    "affected instruments/themes": 2,
    "instrument": 2,
    "theme": 2,
    "ticker": 2,
    "strumento": 2,
    "tema": 2,
    "impact": 3,
    "impatto": 3,
    "source": 4,
    "[n]": 4,
    "ref": 4,
    "citazione": 4,
}

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
    "snapshot della performance watchlist": "performance",
    "scatto della performance della watchlist": "performance",
    "prestazioni della watchlist": "performance",
    "what's driving the moves": "drivers",
    "whats driving the moves": "drivers",
    "cosa guida i movimenti": "drivers",
    "medium-term outlook": "outlook",
    "outlook a medio termine": "outlook",
    "prospettive a medio termine": "outlook",
    "event calendar": "calendar",
    "calendario eventi": "calendar",
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


def section_title(section_key: str, *, language: str = "English") -> str:
    return localized_section_heading(section_key, language)


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


def calendar_section_titles() -> set[str]:
    return _section_title_keys("calendar")


def _normalize_title(title: str) -> str:
    return title.strip().lower()


def _remove_duplicate_sections(content: str, section_key: str) -> str:
    """Keep the first section matching section_key; drop later duplicates."""
    keys = _section_title_keys(section_key)
    sections = _find_sections(content)
    matches = [
        (start, end, level, title)
        for start, end, level, title in sections
        if _normalize_title(title) in keys
    ]
    if len(matches) <= 1:
        return content
    updated = content
    for start, end, _, _ in reversed(matches[1:]):
        updated = updated[:start] + updated[end:]
    return updated


def _rename_section_heading(
    content: str,
    section_key: str,
    *,
    language: str,
) -> str:
    """Normalize the first matching section heading to the canonical localized title."""
    canonical = localized_section_heading(section_key, language)
    keys = _section_title_keys(section_key)
    sections = _find_sections(content)
    for start, end, level, title in sections:
        if _normalize_title(title) not in keys:
            continue
        if title.strip() == canonical:
            return content
        marker = "#" * level
        old_heading = f"{marker} {title}"
        new_heading = f"{marker} {canonical}"
        return content.replace(old_heading, new_heading, 1)
    return content


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

    cited = {int(value) for value in CITATION_RE.findall(body)}
    research_cited = sorted(number for number in cited if number > instrument_count)

    research_formatted = [
        f"{number}. {merged[number]}"
        for number in research_cited
        if number in merged
    ]
    all_refs = yahoo_refs + research_formatted
    refs_text = heading + "\n\n" + "\n".join(all_refs)
    if tail.strip():
        return before.rstrip() + "\n\n" + refs_text + "\n\n" + tail.lstrip("\n")
    return before.rstrip() + "\n\n" + refs_text + "\n"


def parse_material_impacts(
    material_news_input: str,
) -> tuple[list[str], list[str]]:
    """Return instrument labels marked HIGH and MEDIUM in prefetch material brief."""
    high: list[str] = []
    medium: list[str] = []
    for match in MATERIAL_IMPACT_RE.finditer(material_news_input):
        label, level = match.group(1), match.group(2)
        if level == "HIGH":
            high.append(label)
        elif level == "MEDIUM":
            medium.append(label)
    return high[:2], medium


def enforce_high_tag_cap(content: str, material_news_input: str) -> str:
    """Cap 🔴 tags to HIGH-impact instruments (max 2) when the model over-tags."""
    if content.count("🔴") <= 2:
        return content

    high_labels, medium_labels = parse_material_impacts(material_news_input)
    kept_high = 0
    updated_lines: list[str] = []

    for line in content.splitlines():
        if "🔴" not in line:
            updated_lines.append(line)
            continue

        is_high = any(label in line for label in high_labels)
        is_medium = any(label in line for label in medium_labels)

        if is_high and kept_high < 2:
            kept_high += 1
            updated_lines.append(line)
            continue

        new_line = line.replace("🔴", "🟠" if is_medium else "", 1)
        if not is_medium:
            new_line = re.sub(r"\s*HIGH\s*—\s*", " ", new_line)
        new_line = re.sub(r"\s{2,}", " ", new_line).strip()
        updated_lines.append(new_line)

    return "\n".join(updated_lines)


def renumber_citations(
    content: str,
    instrument_count: int,
    seed_refs: dict[int, str],
) -> tuple[str, dict[int, int]]:
    """Renumber research citations (> instrument_count) without gaps."""
    cited_order: list[int] = []
    seen: set[int] = set()
    for match in CITATION_RE.finditer(content):
        number = int(match.group(1))
        if number <= instrument_count or number in seen:
            continue
        seen.add(number)
        cited_order.append(number)

    ordered_old = list(cited_order)

    mapping: dict[int, int] = {}
    next_number = instrument_count + 1
    for old in ordered_old:
        mapping[old] = next_number
        next_number += 1

    if not mapping or all(old == new for old, new in mapping.items()):
        return content, {}

    def _replace_citations(text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            number = int(match.group(1))
            if number in mapping:
                return f"[{mapping[number]}]"
            return match.group(0)

        return CITATION_RE.sub(repl, text)

    updated = _replace_citations(content)

    def _renumber_ref_line(match: re.Match[str]) -> str:
        number = int(match.group(1))
        if number in mapping:
            return f"{mapping[number]}. {match.group(2)}"
        return match.group(0)

    updated = NUMBERED_REF_RE.sub(_renumber_ref_line, updated)
    return updated, mapping


def _parse_table_cells(row: str) -> list[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]


def _ensure_pipe_row(row: str) -> str:
    """Wrap a markdown table row with leading/trailing pipes when missing."""
    stripped = row.strip()
    if not stripped:
        return stripped
    if not stripped.startswith("|"):
        stripped = f"| {stripped.lstrip('|').strip()}"
    if not stripped.endswith("|"):
        stripped = f"{stripped.rstrip('|').strip()} |"
    return stripped


_TABLE_SEPARATOR_RE = re.compile(r"^\|?[-:| ]+\|?\s*$")


def _find_calendar_table_rows(calendar_block: str) -> list[str] | None:
    """Locate a calendar markdown table, including LLM rows with inconsistent pipes."""
    lines = calendar_block.splitlines()
    for index, line in enumerate(lines):
        if not _TABLE_SEPARATOR_RE.match(line.strip()):
            continue
        if index == 0:
            continue
        header = lines[index - 1].strip()
        if "|" not in header:
            continue
        data_rows: list[str] = []
        for row in lines[index + 1 :]:
            stripped = row.strip()
            if not stripped:
                break
            if stripped.startswith("#"):
                break
            if "|" not in stripped:
                break
            data_rows.append(stripped)
        if not data_rows:
            continue
        return [
            _ensure_pipe_row(header),
            _ensure_pipe_row(line.strip()),
            *(_ensure_pipe_row(row) for row in data_rows),
        ]
    return None


def _headers_match_canonical(headers: list[str]) -> bool:
    normalized = [header.strip().lower() for header in headers]
    canonical = [header.lower() for header in CANONICAL_CALENDAR_HEADERS]
    return normalized == canonical


def _remap_calendar_headers(headers: list[str]) -> list[int] | None:
    """Return source-column index for each canonical column, or None if unmappable."""
    source_to_canonical: dict[int, int] = {}
    for source_idx, header in enumerate(headers):
        canonical_idx = CALENDAR_HEADER_ALIASES.get(header.strip().lower())
        if canonical_idx is None:
            return None
        if canonical_idx in source_to_canonical.values():
            return None
        source_to_canonical[source_idx] = canonical_idx

    if len(source_to_canonical) != len(headers):
        return None

    mapped_canonical = set(source_to_canonical.values())
    if mapped_canonical == set(range(len(CANONICAL_CALENDAR_HEADERS))):
        pad_citation_column = False
    elif mapped_canonical == set(range(len(CANONICAL_CALENDAR_HEADERS) - 1)):
        pad_citation_column = True
    else:
        return None

    canonical_to_source = [0] * len(CANONICAL_CALENDAR_HEADERS)
    for source_idx, canonical_idx in source_to_canonical.items():
        canonical_to_source[canonical_idx] = source_idx
    if pad_citation_column:
        canonical_to_source[4] = -1
    return canonical_to_source


def normalize_calendar_table(content: str) -> str:
    """Normalize Event Calendar markdown tables to canonical column names."""
    _, calendar_block, _ = _split_before_section(content, calendar_section_titles())
    if not calendar_block:
        return content

    rows = _find_calendar_table_rows(calendar_block)
    if not rows or len(rows) < 3:
        return content

    old_table = _find_calendar_table_text_for_replace(calendar_block) or "\n".join(rows)
    headers = _parse_table_cells(rows[0])

    if _headers_match_canonical(headers):
        new_table = "\n".join(rows)
        if old_table != new_table:
            return content.replace(old_table, new_table, 1)
        return content

    column_map = _remap_calendar_headers(headers)
    if column_map is None:
        return content

    canonical_rows = [
        "| " + " | ".join(CANONICAL_CALENDAR_HEADERS) + " |",
        "| " + " | ".join("---" for _ in CANONICAL_CALENDAR_HEADERS) + " |",
    ]
    for row in rows[2:]:
        cells = _parse_table_cells(row)
        if len(cells) != len(headers):
            continue
        remapped = []
        for canonical_index in range(len(CANONICAL_CALENDAR_HEADERS)):
            source_idx = column_map[canonical_index]
            if source_idx < 0:
                remapped.append("")
            elif source_idx < len(cells):
                remapped.append(cells[source_idx])
            else:
                remapped.append("")
        canonical_rows.append("| " + " | ".join(remapped) + " |")

    new_table = "\n".join(canonical_rows)
    return content.replace(old_table, new_table, 1)


def _find_calendar_table_text_for_replace(calendar_block: str) -> str | None:
    """Return the raw table substring in the calendar block (any pipe style)."""
    lines = calendar_block.splitlines()
    for index, line in enumerate(lines):
        if not _TABLE_SEPARATOR_RE.match(line.strip()):
            continue
        if index == 0:
            continue
        header = lines[index - 1].strip()
        if "|" not in header:
            continue
        end = index + 1
        while end < len(lines):
            stripped = lines[end].strip()
            if not stripped or stripped.startswith("#") or "|" not in stripped:
                break
            end += 1
        return "\n".join(lines[index - 1 : end])
    return None


def calendar_table_normalization_warning(content: str) -> str | None:
    """Return a warning when the calendar table headers could not be normalized."""
    _, calendar_block, _ = _split_before_section(content, calendar_section_titles())
    if not calendar_block:
        return None

    rows = _find_calendar_table_rows(calendar_block)
    if not rows or len(rows) < 2:
        return None

    headers = _parse_table_cells(rows[0])
    if _headers_match_canonical(headers):
        return None
    if _remap_calendar_headers(headers) is not None:
        return None
    return (
        "Event Calendar table headers could not be mapped to canonical columns; "
        f"found: {headers}"
    )


def validate_citations(
    content: str,
    *,
    reference_count: int,
    instrument_count: int = 0,
) -> list[str]:
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

    if instrument_count > 0:
        research_used = sorted(number for number in used if number > instrument_count)
        if research_used:
            expected = list(
                range(instrument_count + 1, instrument_count + 1 + len(research_used))
            )
            if research_used != expected:
                warnings.append(
                    "Research citation numbering has gaps: "
                    f"found {research_used}, expected {expected}"
                )

    return warnings


def validate_material_news_prominence(content: str, inputs: dict[str, str]) -> list[str]:
    """Warn when HIGH material news may have been diluted or replaced in narrative."""
    material = inputs.get("watchlist_material_news", "")
    if "Impact **HIGH**" not in material:
        return []

    warnings: list[str] = []
    lowered = content.lower()
    vague_markers = (
        "speculaz",
        "speculation",
        "incertezze nel settore",
        "sector uncertainty",
        "competizione nel settore",
        "sector competition",
    )
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
        seen_tickers: set[str] = set()
        for entry in seed:
            ticker = (entry.get("ticker") or "").strip()
            if not ticker or ticker in seen_tickers:
                continue
            seen_tickers.add(ticker)
            url = (entry.get("url") or "").lower()
            title = (entry.get("title") or "").strip()
            if not title or not any(domain in url for domain in OFFICIAL_DOMAINS):
                continue
            title_snippet = title[:40].lower()
            if title_snippet and title_snippet not in lowered:
                warnings.append(
                    f"Prefetch top headline for {ticker} is from an institutional source "
                    f"({entry.get('url', '')}) but its title does not appear in the briefing — "
                    "verify the correct issuer story is reported."
                )

    return warnings


def postprocess_briefing(content: str, inputs: dict[str, str]) -> tuple[str, list[str]]:
    """Apply deterministic fixes to a generated briefing markdown document."""
    updated = content

    context = json.loads(inputs["watchlist_context"])
    if inputs.get("watchlist_instruments_json"):
        instruments = json.loads(inputs["watchlist_instruments_json"])
    else:
        instruments = context["instruments"]
    language = inputs.get("language", context.get("language", "English"))
    date_str = inputs.get("current_date", context.get("current_date", ""))
    instrument_count = len(instruments)

    performance_table = inputs.get("watchlist_performance_table", "")
    highlights = build_performance_highlights(instruments, language=language)
    performance_body = performance_table
    if highlights:
        performance_body = f"{highlights}\n\n{performance_table}"

    charts_md = inputs.get("watchlist_performance_charts_md", "")
    if charts_md:
        performance_body = f"{performance_body}\n\n{charts_md}"

    before_perf = updated
    updated = _remove_duplicate_sections(updated, "performance")
    updated = _replace_section_body(
        updated,
        title_keys=performance_section_titles(),
        new_body=performance_body,
    )
    updated = _rename_section_heading(updated, "performance", language=language)
    updated = _remove_duplicate_sections(updated, "performance")

    updated = enforce_high_tag_cap(
        updated, inputs.get("watchlist_material_news", "")
    )
    updated = normalize_calendar_table(updated)
    calendar_warning = calendar_table_normalization_warning(updated)
    if updated == before_perf and performance_table:
        exec_keys = _section_title_keys("executive_summary")
        sections = _find_sections(updated)
        for start, end, level, title in sections:
            if _normalize_title(title) not in exec_keys:
                continue
            perf_heading = f"## {section_title('performance', language=language)}"
            insert = f"\n\n{perf_heading}\n\n{performance_body.strip()}\n\n"
            updated = updated[:end].rstrip() + insert + updated[end:].lstrip("\n")
            break

    yahoo_refs = build_market_data_references(instruments, date_str=date_str)
    seed_refs = _load_seed_references(inputs)
    updated, citation_remap = renumber_citations(
        updated, instrument_count, seed_refs
    )
    if citation_remap:
        seed_refs = {
            citation_remap.get(old, old): text
            for old, text in seed_refs.items()
        }

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
    warnings = validate_citations(
        body or updated,
        reference_count=reference_count,
        instrument_count=instrument_count,
    )
    if calendar_warning:
        warnings.append(calendar_warning)
    warnings.extend(validate_material_news_prominence(updated, inputs))
    return updated, warnings
