"""Domain models for resolved instrument identity."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Listing:
    ticker: str
    exchange: str
    currency: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class InstrumentIdentity:
    isin: str
    instrument_type: str
    name: str
    primary_ticker: str
    exchange: str
    currency: str
    listings: list[Listing] = field(default_factory=list)
    sector: str | None = None
    industry: str | None = None
    benchmark: str | None = None
    issuer: str | None = None
    resolved_at: str = ""
    last_verified_at: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["listings"] = [listing.to_dict() for listing in self.listings]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstrumentIdentity":
        listings = [Listing(**item) for item in data.get("listings", [])]
        return cls(
            isin=data["isin"],
            instrument_type=data["instrument_type"],
            name=data["name"],
            primary_ticker=data["primary_ticker"],
            exchange=data["exchange"],
            currency=data.get("currency", ""),
            listings=listings,
            sector=data.get("sector"),
            industry=data.get("industry"),
            benchmark=data.get("benchmark"),
            issuer=data.get("issuer"),
            resolved_at=data.get("resolved_at", ""),
            last_verified_at=data.get("last_verified_at", ""),
            source=data.get("source", ""),
        )
