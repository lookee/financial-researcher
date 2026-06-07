"""Resolve ISIN codes to tickers and enrich identity via OpenFIGI and Yahoo Finance."""

import os
from datetime import date

import requests
import yfinance as yf

from financial_researcher.models.instrument import InstrumentIdentity, Listing
from financial_researcher.storage.identity_store import IdentityStore

OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"

# Map exchange codes to Yahoo Finance ticker suffixes (suffix tried before bare ticker).
EXCHANGE_SUFFIX = {
    "GR": ".MI",
    "IM": ".MI",
    "MI": ".MI",
    "MIL": ".MI",
    "DE": ".DE",
    "GA": ".DE",
    "AS": ".AS",
    "LSE": ".L",
    "LN": ".L",
}


class IsinResolver:
    """Resolve and cache instrument identity from ISIN."""

    def __init__(self, store: IdentityStore | None = None):
        self.store = store or IdentityStore()

    def resolve(
        self,
        isin: str,
        force_refresh: bool = False,
        preferred_ticker: str | None = None,
        manual_ticker: str | None = None,
        manual_type: str | None = None,
    ) -> InstrumentIdentity:
        isin = isin.strip().upper()
        fallback_ticker = manual_ticker or preferred_ticker

        if not force_refresh:
            cached = self.store.get(isin)
            if cached and not self.store.needs_verification(cached):
                if preferred_ticker and cached.primary_ticker != preferred_ticker:
                    cached.primary_ticker = preferred_ticker
                    cached = self._enrich_with_yfinance(cached)
                    return self.store.save(cached)
                return cached

        try:
            identity = self._resolve_via_openfigi(isin)
        except Exception:
            if fallback_ticker:
                identity = self._build_from_ticker(
                    isin=isin,
                    ticker=fallback_ticker,
                    instrument_type=manual_type or "stock",
                    source="manual_fallback",
                )
                return self.store.save(identity)
            cached = self.store.get(isin)
            if cached:
                return self.store.touch_verified(cached)
            raise ValueError(
                f"Unable to resolve ISIN {isin}. "
                "Provide ticker and exchange manually."
            )

        if preferred_ticker:
            identity.primary_ticker = preferred_ticker

        identity = self._enrich_with_yfinance(identity)
        return self.store.save(identity)

    def _resolve_via_openfigi(self, isin: str) -> InstrumentIdentity:
        headers = {"Content-Type": "application/json"}
        api_key = os.getenv("OPENFIGI_API_KEY")
        if api_key:
            headers["X-OPENFIGI-APIKEY"] = api_key

        response = requests.post(
            OPENFIGI_URL,
            headers=headers,
            json=[{"idType": "ID_ISIN", "idValue": isin}],
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload or not payload[0].get("data"):
            raise ValueError(f"OpenFIGI returned no results for {isin}")

        entries = payload[0]["data"]
        primary = entries[0]
        listings = [
            Listing(
                ticker=item.get("ticker", ""),
                exchange=item.get("exchCode", ""),
                currency=item.get("currency", ""),
            )
            for item in entries
            if item.get("ticker")
        ]
        security_type = (primary.get("securityType2") or primary.get("securityType") or "").lower()
        instrument_type = "etf" if "etf" in security_type or "fund" in security_type else "stock"

        return InstrumentIdentity(
            isin=isin,
            instrument_type=instrument_type,
            name=primary.get("name", isin),
            primary_ticker=primary.get("ticker", ""),
            exchange=primary.get("exchCode", ""),
            currency=primary.get("currency", ""),
            listings=listings,
            resolved_at=date.today().isoformat(),
            last_verified_at=date.today().isoformat(),
            source="openfigi",
        )

    def _build_from_ticker(
        self,
        isin: str,
        ticker: str,
        instrument_type: str,
        source: str,
    ) -> InstrumentIdentity:
        identity = InstrumentIdentity(
            isin=isin,
            instrument_type=instrument_type,
            name=ticker,
            primary_ticker=ticker,
            exchange="",
            currency="",
            listings=[Listing(ticker=ticker, exchange="", currency="")],
            source=source,
        )
        return self._enrich_with_yfinance(identity)

    def _yahoo_candidates(self, identity: InstrumentIdentity) -> list[str]:
        candidates: list[str] = []
        seen: set[str] = set()

        def add(ticker: str, exchange: str = "") -> None:
            if not ticker or ticker in seen:
                return
            if "." in ticker:
                seen.add(ticker)
                candidates.append(ticker)
                return
            suffix = EXCHANGE_SUFFIX.get(exchange.upper(), "")
            if suffix:
                combined = f"{ticker}{suffix}"
                if combined not in seen:
                    seen.add(combined)
                    candidates.append(combined)
            if ticker not in seen:
                seen.add(ticker)
                candidates.append(ticker)

        add(identity.primary_ticker, identity.exchange)
        for listing in identity.listings:
            add(listing.ticker, listing.exchange)
        return candidates

    def _enrich_with_yfinance(self, identity: InstrumentIdentity) -> InstrumentIdentity:
        info: dict = {}
        working_ticker = identity.primary_ticker

        if identity.instrument_type == "etf":
            for candidate in self._yahoo_candidates(identity):
                candidate_info = yf.Ticker(candidate).info or {}
                quote_type = (candidate_info.get("quoteType") or "").upper()
                has_price = bool(
                    candidate_info.get("regularMarketPrice")
                    or candidate_info.get("currentPrice")
                )
                if quote_type == "ETF" and has_price:
                    info = candidate_info
                    working_ticker = candidate
                    break

        if not info:
            for candidate in self._yahoo_candidates(identity):
                candidate_info = yf.Ticker(candidate).info or {}
                quote_type = (candidate_info.get("quoteType") or "").upper()
                if (
                    identity.instrument_type == "etf"
                    and quote_type == "EQUITY"
                    and (
                        candidate_info.get("regularMarketPrice")
                        or candidate_info.get("currentPrice")
                    )
                ):
                    continue
                if candidate_info.get("regularMarketPrice") or candidate_info.get(
                    "currentPrice"
                ):
                    info = candidate_info
                    working_ticker = candidate
                    break
                if candidate_info.get("longName") or candidate_info.get("shortName"):
                    info = candidate_info
                    working_ticker = candidate

        identity.primary_ticker = working_ticker

        identity.name = info.get("longName") or info.get("shortName") or identity.name
        identity.currency = info.get("currency") or identity.currency
        identity.exchange = info.get("exchange") or identity.exchange
        identity.sector = info.get("sector")
        identity.industry = info.get("industry")

        quote_type = (info.get("quoteType") or "").upper()
        if quote_type == "ETF":
            identity.instrument_type = "etf"
            identity.benchmark = info.get("category") or info.get("fundFamily")
            identity.issuer = info.get("fundFamily")

        if identity.source == "openfigi":
            identity.source = "openfigi+yfinance"

        return identity
