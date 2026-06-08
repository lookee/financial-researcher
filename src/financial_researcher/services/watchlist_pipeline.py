"""Load watchlist, resolve instruments, and fetch market data."""

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
from financial_researcher.settings import get_default_language

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

        identities: list[InstrumentIdentity] = []
        snapshots: list[dict[str, Any]] = []

        for item in config.get("instruments", []):
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
            identities.append(identity)
            snapshots.append(snapshot)
            print(f"  Loaded {identity.primary_ticker} ({identity.name})")

        if not identities:
            raise ValueError("Watchlist contains no instruments.")

        context = build_watchlist_context(
            identities,
            snapshots,
            session=session,
            language=briefing_language,
        )
        return attach_prefetched_news(context)
