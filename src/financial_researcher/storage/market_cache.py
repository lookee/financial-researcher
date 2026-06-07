"""TTL cache for Yahoo Finance market snapshots."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_MARKET_DIR = Path("data/market")
DEFAULT_TTL_MINUTES = 60


class MarketCache:
    """Store latest market snapshot per ISIN with a configurable TTL."""

    def __init__(
        self,
        base_dir: Path | str = DEFAULT_MARKET_DIR,
        ttl_minutes: int = DEFAULT_TTL_MINUTES,
    ):
        self.base_dir = Path(base_dir)
        self.ttl = timedelta(minutes=ttl_minutes)

    def _path_for(self, isin: str) -> Path:
        directory = self.base_dir / isin.upper()
        directory.mkdir(parents=True, exist_ok=True)
        return directory / "latest.json"

    def get(self, isin: str) -> dict[str, Any] | None:
        path = self._path_for(isin)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        fetched_at = datetime.fromisoformat(payload["fetched_at"])
        if datetime.now(timezone.utc) - fetched_at > self.ttl:
            return None
        return payload

    def save(self, isin: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "isin": isin.upper(),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": snapshot,
        }
        path = self._path_for(isin)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        return payload
