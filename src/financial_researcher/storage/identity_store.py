"""Persist resolved ISIN identity to local JSON files."""

import json
from datetime import date
from pathlib import Path

from financial_researcher.models.instrument import InstrumentIdentity

DEFAULT_IDENTITY_DIR = Path("data/identity")
VERIFY_AFTER_DAYS = 90


class IdentityStore:
    """Read/write InstrumentIdentity records under data/identity/."""

    def __init__(self, base_dir: Path | str = DEFAULT_IDENTITY_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, isin: str) -> Path:
        return self.base_dir / f"{isin.upper()}.json"

    def get(self, isin: str) -> InstrumentIdentity | None:
        path = self._path_for(isin)
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as handle:
            return InstrumentIdentity.from_dict(json.load(handle))

    def save(self, identity: InstrumentIdentity) -> InstrumentIdentity:
        today = date.today().isoformat()
        if not identity.resolved_at:
            identity.resolved_at = today
        identity.last_verified_at = today
        path = self._path_for(identity.isin)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(identity.to_dict(), handle, indent=2, ensure_ascii=False)
        return identity

    def touch_verified(self, identity: InstrumentIdentity) -> InstrumentIdentity:
        identity.last_verified_at = date.today().isoformat()
        return self.save(identity)

    def needs_verification(self, identity: InstrumentIdentity) -> bool:
        if not identity.last_verified_at:
            return True
        last = date.fromisoformat(identity.last_verified_at)
        return (date.today() - last).days >= VERIFY_AFTER_DAYS
