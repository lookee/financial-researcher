"""Load watchlist, resolve instruments, and fetch market data."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

from financial_researcher.models.instrument import InstrumentIdentity
from financial_researcher.paths import ensure_watchlist_exists
from financial_researcher.services.isin_resolver import IsinResolver
from financial_researcher.services.market_data import MarketDataService
from financial_researcher.services.watchlist_context import (
    attach_prefetched_news,
    build_watchlist_context,
)
from financial_researcher.settings import get_default_language, get_pipeline_settings

VALID_SESSIONS = ("pre_open", "post_open", "midday", "close")


def load_watchlist(path: Path | None = None) -> dict[str, Any]:
    watchlist_path = ensure_watchlist_exists(path)
    with watchlist_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


class WatchlistPipeline:
    """Resolve and fetch market data for every instrument in a watchlist."""

    def __init__(
        self,
        resolver: IsinResolver | None = None,
        market: MarketDataService | None = None,
    ):
        self.resolver = resolver or IsinResolver()
        self.market = market or MarketDataService()

    def _collect_one(
        self,
        item: dict[str, Any],
        *,
        force: bool,
    ) -> tuple[InstrumentIdentity, dict[str, Any]]:
        if not item.get("isin"):
            raise ValueError("Each watchlist entry must include isin.")
        if not item.get("ticker"):
            raise ValueError(
                f"Each watchlist entry must include ticker (ISIN {item['isin']})."
            )

        identity = self.resolver.resolve(
            isin=item["isin"],
            force_refresh=force,
            preferred_ticker=item.get("ticker"),
            manual_ticker=item.get("ticker"),
            manual_type=item.get("type"),
        )
        snapshot = self.market.get_snapshot(identity, use_cache=not force)
        print(f"  ▸ {identity.primary_ticker} ({identity.name})")
        return identity, snapshot

    def collect(
        self,
        watchlist_path: Path | None = None,
        *,
        force: bool = False,
        language: str | None = None,
        session: str = "close",
    ) -> dict[str, str]:
        config = load_watchlist(watchlist_path)
        briefing_language = language or config.get("language") or get_default_language()

        if session not in VALID_SESSIONS:
            raise ValueError(
                f"Invalid session {session!r}. "
                f"Choose from: {', '.join(VALID_SESSIONS)}"
            )

        items: list[dict[str, Any]] = list(config.get("instruments", []))
        if not items:
            raise ValueError("Watchlist contains no instruments.")

        max_workers = min(get_pipeline_settings()["max_workers"], len(items))
        results: list[tuple[InstrumentIdentity, dict[str, Any]] | None] = [None] * len(
            items
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._collect_one, item, force=force): index
                for index, item in enumerate(items)
            }
            for future, index in futures.items():
                results[index] = future.result()

        identities = [pair[0] for pair in results if pair is not None]
        snapshots = [pair[1] for pair in results if pair is not None]

        context = build_watchlist_context(
            identities,
            snapshots,
            session=session,
            language=briefing_language,
        )
        return attach_prefetched_news(context)
