"""Normalize publication dates and classify source freshness for news attribution."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

_ISO_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_DMY_SLASH_RE = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})")
_RELATIVE_IT = (
    (re.compile(r"(\d+)\s+giorn[oi]\s+fa", re.I), "days"),
    (re.compile(r"(\d+)\s+day[s]?\s+ago", re.I), "days"),
    (re.compile(r"(\d+)\s+week[s]?\s+ago", re.I), "weeks"),
    (re.compile(r"(\d+)\s+settiman[ae]\s+fa", re.I), "weeks"),
)
_RELATIVE_LOOSE = (
    (re.compile(r"yesterday|ieri", re.I), 1),
    (re.compile(r"today|oggi", re.I), 0),
    (re.compile(r"1\s+week\s+ago|1\s+settimana\s+fa", re.I), 7),
)

CAUSAL_TRADING_DAYS = 3


def normalize_publication_date(raw: str | None, *, as_of: date | None = None) -> str | None:
    """Return YYYY-MM-DD when parseable, else None."""
    if not raw:
        return None
    text = raw.strip()
    if not text or text.lower() in {"n/a", "na", "unknown"}:
        return None

    match = _ISO_DATE_RE.search(text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    anchor = as_of or date.today()
    lowered = text.lower()
    for pattern, unit in _RELATIVE_IT:
        found = pattern.search(lowered)
        if found:
            amount = int(found.group(1))
            if unit == "days":
                return (anchor - timedelta(days=amount)).isoformat()
            if unit == "weeks":
                return (anchor - timedelta(weeks=amount)).isoformat()

    for pattern, days_back in _RELATIVE_LOOSE:
        if pattern.search(lowered):
            return (anchor - timedelta(days=days_back)).isoformat()

    if "week ago" in lowered or "settimana fa" in lowered:
        return (anchor - timedelta(days=7)).isoformat()

    match = _DMY_SLASH_RE.search(text)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    for fmt in ("%b %d, %Y", "%d %b %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text[:20], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def count_trading_days_between(start: date, end: date) -> int:
    """Count weekdays from start (exclusive) to end (inclusive)."""
    if end < start:
        return 0
    cursor = start + timedelta(days=1)
    count = 0
    while cursor <= end:
        if cursor.weekday() < 5:
            count += 1
        cursor += timedelta(days=1)
    return count


def freshness_role(published: str | None, *, as_of: date) -> str:
    """Return 'causal' (≤3 trading days) or 'background' for attribution rules."""
    if not published:
        return "background"
    try:
        published_date = date.fromisoformat(published)
    except ValueError:
        return "background"
    if published_date > as_of:
        return "background"
    trading_days = count_trading_days_between(published_date, as_of)
    return "causal" if trading_days <= CAUSAL_TRADING_DAYS else "background"


def annotate_headline_freshness(
    headline: dict[str, str],
    *,
    as_of: date,
) -> dict[str, str]:
    """Attach normalized publication_date and freshness_role to a headline dict."""
    enriched = dict(headline)
    published = normalize_publication_date(headline.get("date"), as_of=as_of)
    if published:
        enriched["published_date"] = published
        enriched["date"] = published
    role = freshness_role(published, as_of=as_of)
    enriched["freshness_role"] = role
    enriched["freshness_label"] = (
        "CAUSAL (≤3 trading days)" if role == "causal" else "BACKGROUND (profile/context only)"
    )
    return enriched
