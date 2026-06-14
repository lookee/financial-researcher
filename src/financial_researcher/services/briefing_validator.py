"""Post-generation validation for executive briefings (no LLM cost)."""

from __future__ import annotations

import json
import re
from typing import Any

from financial_researcher.services.briefing_postprocess import (
    CITATION_RE,
    HEADING_RE,
    NUMBERED_REF_RE,
    SECTION_ALIASES,
    SECTION_HEADINGS,
    _find_sections,
    _normalize_title,
    _section_title_keys,
)
from financial_researcher.localization import english_section_headings, localized_section_heading

PCT_IN_BODY_RE = re.compile(
    r"([+-]?\d+[,.]\d+|\d+[,.]\d+|\d+)\s*%\s*(?:\s*1[DWMY]|1[DWMY]|YTD|giornaliera|settimanale|mensile|annuale)?",
    re.IGNORECASE,
)


def _load_instruments(inputs: dict[str, str]) -> list[dict[str, Any]]:
    if inputs.get("watchlist_instruments_json"):
        return json.loads(inputs["watchlist_instruments_json"])
    context = json.loads(inputs["watchlist_context"])
    return context["instruments"]


def validate_citation_coverage(content: str, *, reference_count: int) -> list[str]:
    """Every body [n] must exist in References; every reference should be cited."""
    warnings: list[str] = []
    body, refs_block, _ = _split_refs(content)
    if not refs_block:
        return ["References section missing."]

    listed = {int(m.group(1)) for m in NUMBERED_REF_RE.finditer(refs_block)}
    cited = {int(m.group(1)) for m in CITATION_RE.finditer(body)}

    orphan_citations = sorted(cited - listed)
    if orphan_citations:
        warnings.append(
            f"Body cites [{orphan_citations}] not found in References."
        )

    unused_refs = sorted(n for n in listed if n not in cited and n <= reference_count)
    if unused_refs and len(unused_refs) <= 8:
        warnings.append(f"References never cited in body: {unused_refs}")

    return warnings


def _split_refs(content: str) -> tuple[str, str, str]:
    from financial_researcher.services.briefing_postprocess import (
        references_section_titles,
        _split_before_section,
    )

    return _split_before_section(content, references_section_titles())


def validate_performance_figures(
    content: str,
    instruments: list[dict[str, Any]],
    *,
    tolerance: float = 0.15,
) -> list[str]:
    """Warn when cited 1D/1W/1M/YTD percentages diverge from the data layer."""
    warnings: list[str] = []
    mismatches: list[str] = []

    for item in instruments:
        perf = item.get("performance", {})
        for horizon in ("1d", "1w", "1m", "ytd"):
            value = perf.get(horizon)
            if value is None:
                continue
            for match in PCT_IN_BODY_RE.finditer(content):
                raw = match.group(1).replace(",", ".")
                try:
                    cited = float(raw)
                except ValueError:
                    continue
                if abs(cited - value) <= tolerance:
                    break
            else:
                if abs(value) >= 0.05:
                    mismatches.append(
                        f"{item['ticker']} {horizon.upper()}={value:.2f}% "
                        "not matched in memo"
                    )

    if mismatches:
        warnings.append(
            "Performance figure mismatches (vs data layer): "
            + "; ".join(mismatches[:6])
        )
    return warnings


def validate_section_language(content: str, *, language: str) -> list[str]:
    """Detect duplicate sections and English headings in non-English briefings."""
    warnings: list[str] = []
    sections = _find_sections(content)
    seen_keys: dict[str, int] = {}

    for _, _, _, title in sections:
        normalized = _normalize_title(title)
        section_key = SECTION_ALIASES.get(normalized)
        if not section_key:
            for key, heading in SECTION_HEADINGS.items():
                if normalized == heading.lower():
                    section_key = key
                    break
        if section_key:
            seen_keys[section_key] = seen_keys.get(section_key, 0) + 1

    for key, count in seen_keys.items():
        if count > 1:
            warnings.append(
                f"Duplicate section '{localized_section_heading(key, language)}' "
                f"appears {count} times."
            )
    return warnings


def validate_briefing(
    content: str,
    inputs: dict[str, str],
) -> list[str]:
    """Run all post-generation checks; returns warning strings."""
    instruments = _load_instruments(inputs)
    language = inputs.get("language", "English")

    _, refs_block, _ = _split_refs(content)
    reference_count = len(NUMBERED_REF_RE.findall(refs_block or ""))

    warnings: list[str] = []
    warnings.extend(validate_citation_coverage(content, reference_count=reference_count))
    warnings.extend(validate_performance_figures(content, instruments))
    warnings.extend(validate_section_language(content, language=language))
    return warnings


def format_validation_summary(warnings: list[str]) -> str:
    if not warnings:
        return "Validation: OK (0 warnings)"
    return f"Validation: {len(warnings)} warning(s)"
