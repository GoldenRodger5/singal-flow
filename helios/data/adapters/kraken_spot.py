"""Kraken Spot adapter — public OHLC for cash-and-carry's spot leg.

Endpoint: https://api.kraken.com/0/public/OHLC?pair=...&interval=60&since=...
Returns up to ~720 candles per call; we paginate forward with `since`.

Pair codes vary: BTC=XBTUSD, ETH=XETHZUSD (legacy), SOL=SOLUSD. The
PAIR_MAP below normalizes to a canonical Kraken Futures perp instrument
(PF_XBTUSD / PF_ETHUSD / PF_SOLUSD) for join-friendliness in A8.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import httpx

from helios.data.adapters.base import Bar, VenueError
from helios.ops import get_logger
from helios.types import Venue

log = get_logger(__name__)

KRAKEN_SPOT_PUBLIC = "https://api.kraken.com/0/public"

# Map Kraken Futures perp instrument code -> (spot_pair_query, spot_pair_key, canonical_symbol)
PAIR_MAP = {
    "PF_XBTUSD":  ("XBTUSD", "XXBTZUSD",  "PF_XBTUSD"),
    "PF_ETHUSD":  ("ETHUSD", "XETHZUSD",  "PF_ETHUSD"),
    "PF_SOLUSD":  ("SOLUSD", "SOLUSD",    "PF_SOLUSD"),
}

_INTERVAL_MAP_MIN = {
    "1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440,
}


class KrakenSpotMarketData:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=20.0)

    async def fetch_bars(
        self, perp_symbol: str, interval: str, start: datetime, end: datetime
    ) -> list[Bar]:
        """Fetch spot OHLC for the spot pair corresponding to `perp_symbol`.

        Pagination: Kraken returns the `last` cursor in its response; we advance
        `since` to the last bar's timestamp and re-request until we reach `end`.
        """
        if perp_symbol not in PAIR_MAP:
            raise ValueError(f"No spot mapping for perp {perp_symbol!r}")
        query_pair, _, canonical = PAIR_MAP[perp_symbol]
        interval_min = _INTERVAL_MAP_MIN.get(interval)
        if interval_min is None:
            raise ValueError(f"Unsupported interval {interval!r}")

        all_bars: list[Bar] = []
        seen: set[int] = set()
        since = int(start.timestamp())
        end_ts = int(end.timestamp())

        # Safety: cap number of pages to avoid runaway loop
        max_pages = 200
        for _ in range(max_pages):
            if since >= end_ts:
                break
            params = {"pair": query_pair, "interval": interval_min, "since": since}
            try:
                resp = await self._client.get(f"{KRAKEN_SPOT_PUBLIC}/OHLC", params=params)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise VenueError(f"Kraken Spot OHLC failed for {query_pair}: {e}") from e

            body = resp.json()
            if body.get("error"):
                raise VenueError(f"Kraken Spot OHLC error: {body['error']}")
            result = body.get("result", {})
            # The pair key may differ from query name (XBTUSD -> XXBTZUSD)
            data_key = next((k for k in result if k != "last"), None)
            if data_key is None:
                break
            rows = result[data_key]
            if not rows:
                break
            available_at = datetime.now(timezone.utc)
            advanced = False
            for r in rows:
                t_sec = int(r[0])
                if t_sec in seen or t_sec > end_ts:
                    continue
                seen.add(t_sec)
                t = datetime.fromtimestamp(t_sec, tz=timezone.utc)
                all_bars.append(Bar(
                    symbol=canonical,
                    venue=Venue.KRAKEN_SPOT,
                    interval=interval,
                    open=Decimal(str(r[1])),
                    high=Decimal(str(r[2])),
                    low=Decimal(str(r[3])),
                    close=Decimal(str(r[4])),
                    volume=Decimal(str(r[6])),
                    event_time=t,
                    available_at=max(available_at, t),
                ))
                advanced = True
            new_since = int(result.get("last", since))
            if new_since <= since or not advanced:
                break
            since = new_since

        all_bars.sort(key=lambda b: b.event_time)
        return all_bars

    async def close(self) -> None:
        await self._client.aclose()
