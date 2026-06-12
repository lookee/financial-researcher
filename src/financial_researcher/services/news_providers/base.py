"""Shared types for external news providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedHeadline:
    date: str
    title: str
    source: str
    url: str
    summary: str
    region: str
    provider: str

    def to_dict(self) -> dict[str, str]:
        """Convert to the headline dict shape used by news_prefetch / news_ranking."""
        return {
            "date": self.date,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "summary": self.summary,
            "region": self.region,
            "provider": self.provider,
        }


def headline_dicts(items: list[NormalizedHeadline]) -> list[dict[str, str]]:
    return [item.to_dict() for item in items]
