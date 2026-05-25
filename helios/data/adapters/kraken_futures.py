"""Kraken Futures adapter — CFTC-regulated venue, our primary perp execution venue.

Auth model: API key + secret (HMAC-SHA512 signing per Kraken Futures docs).
Read-only key is enough for market data; trading needs full key + 2FA.

Phase 1 implementation: REST historical bars only (no auth). Streaming and
order placement arrive in Phase 2 once keys are provisioned and the paper
gate is passed.

API reference: https://docs.kraken.com/api/docs/futures-api/trading/
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncIterator

import httpx

from helios.data.adapters.base import Bar, MarketDataSource, Tick, VenueError
from helios.ops import get_logger
from helios.types import Venue

log = get_logger(__name__)

KRAKEN_FUTURES_PUBLIC = "https://futures.kraken.com/api/charts/v1"
KRAKEN_FUTURES_DERIVATIVES = "https://futures.kraken.com/derivatives/api/v4"


@dataclass(frozen=True, slots=True)
class FundingRecord:
    symbol: str
    funding_rate: float
    event_time: datetime
    available_at: datetime


# Interval → Kraken Futures "resolution" param
_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


class KrakenFuturesMarketData(MarketDataSource):
    """Read-only market-data client for Kraken Futures.

    No auth required for OHLC endpoints. We construct `available_at` as the
    response receive time so the PIT layer treats backfilled historical bars
    consistently with live streamed bars.
    """

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=20.0)

    async def fetch_bars(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> list[Bar]:
        """Fetch hourly/etc bars. Kraken caps each response at ~5000 candles, so
        we chunk the request window backwards from `end` until we cover `start`."""
        resolution = _INTERVAL_MAP.get(interval)
        if resolution is None:
            raise ValueError(f"Unsupported interval {interval!r}")

        seconds_per_bar = {
            "1m": 60, "5m": 300, "15m": 900,
            "1h": 3600, "4h": 14400, "1d": 86400,
        }[interval]
        # Stay under Kraken's per-response cap with a conservative window
        chunk_bars = 4000
        chunk_seconds = chunk_bars * seconds_per_bar

        url = f"{KRAKEN_FUTURES_PUBLIC}/trade/{symbol}/{resolution}"
        all_bars: list[Bar] = []
        seen_times: set[int] = set()
        cursor = int(end.timestamp())
        floor = int(start.timestamp())

        while cursor > floor:
            chunk_from = max(floor, cursor - chunk_seconds)
            params = {"from": chunk_from, "to": cursor}
            try:
                resp = await self._client.get(url, params=params)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise VenueError(f"Kraken Futures bars fetch failed for {symbol} {interval}: {e}") from e

            available_at = datetime.now(timezone.utc)
            body = resp.json()
            candles = body.get("candles", [])
            if not candles:
                break
            earliest = None
            for c in candles:
                t_ms = int(c["time"])
                if t_ms in seen_times:
                    continue
                seen_times.add(t_ms)
                t = datetime.fromtimestamp(t_ms / 1000.0, tz=timezone.utc)
                if earliest is None or t < earliest:
                    earliest = t
                all_bars.append(Bar(
                    symbol=symbol, venue=Venue.KRAKEN_FUTURES, interval=interval,
                    open=Decimal(str(c["open"])), high=Decimal(str(c["high"])),
                    low=Decimal(str(c["low"])), close=Decimal(str(c["close"])),
                    volume=Decimal(str(c["volume"])),
                    event_time=t, available_at=max(available_at, t),
                ))
            if earliest is None:
                break
            new_cursor = int(earliest.timestamp())
            # If we made no backwards progress, bail to avoid infinite loop
            if new_cursor >= cursor:
                break
            cursor = new_cursor

        all_bars.sort(key=lambda b: b.event_time)
        return all_bars

    async def fetch_funding(self, symbol: str) -> list[FundingRecord]:
        """Historical funding rates for a perpetual.

        Kraken's public endpoint returns the full history (no from/to params).
        Funding settles every hour on Kraken Futures (some venues are 8h).
        """
        url = f"{KRAKEN_FUTURES_DERIVATIVES}/historicalfundingrates"
        try:
            resp = await self._client.get(url, params={"symbol": symbol})
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise VenueError(f"Kraken Futures funding fetch failed for {symbol}: {e}") from e

        body = resp.json()
        if body.get("result") != "success":
            raise VenueError(f"Kraken funding API error: {body!r}")
        available_at = datetime.now(timezone.utc)
        records: list[FundingRecord] = []
        for r in body.get("rates", []):
            # Per docs: timestamp is ISO-8601, fundingRate is relative to mark
            ts_raw = r.get("timestamp")
            if not ts_raw:
                continue
            t = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            # Either "fundingRate" or "relativeFundingRate" may appear; prefer relative
            fr = r.get("relativeFundingRate")
            if fr is None:
                fr = r.get("fundingRate")
            if fr is None:
                continue
            records.append(FundingRecord(
                symbol=symbol,
                funding_rate=float(fr),
                event_time=t,
                available_at=max(available_at, t),
            ))
        records.sort(key=lambda r: r.event_time)
        return records

    async def stream_bars(self, symbol: str, interval: str) -> AsyncIterator[Bar]:  # pragma: no cover
        raise NotImplementedError("Streaming bars: Phase 2 (after auth + WS plumbing)")

    async def stream_ticks(self, symbol: str) -> AsyncIterator[Tick]:  # pragma: no cover
        raise NotImplementedError("Streaming ticks: Phase 2")

    async def close(self) -> None:
        await self._client.aclose()


def kraken_futures_keys() -> tuple[str, str] | None:
    """Returns (key, secret) from env or None if not provisioned.

    Trading endpoints need both. Market-data endpoints need neither.
    """
    k = os.getenv("KRAKEN_FUTURES_API_KEY")
    s = os.getenv("KRAKEN_FUTURES_API_SECRET")
    if k and s:
        return (k, s)
    return None
