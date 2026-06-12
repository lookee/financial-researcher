"""Serper query helpers (free-tier sanitisation)."""

from __future__ import annotations

import re

_SITE_OPERATOR_RE = re.compile(r"\bsite:\S+", re.IGNORECASE)
_QUOTED_PHRASE_RE = re.compile(r'"([^"]+)"')


def sanitize_serper_query(query: str, *, free_tier: bool = True) -> str:
    """Simplify queries rejected by Serper free plans (site:, long OR chains)."""
    cleaned = (query or "").strip()
    if not cleaned or not free_tier:
        return cleaned

    cleaned = _SITE_OPERATOR_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if re.search(r"\bor\b", cleaned, flags=re.IGNORECASE):
        quoted = _QUOTED_PHRASE_RE.findall(cleaned)
        if quoted:
            cleaned = quoted[0]
        else:
            cleaned = re.split(r"\bor\b", cleaned, maxsplit=1, flags=re.IGNORECASE)[0].strip()

    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    return cleaned
