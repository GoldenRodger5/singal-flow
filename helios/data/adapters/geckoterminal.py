"""GeckoTerminal adapter — free, no-key historical OHLCV for Solana DEX pools.

Replaces Birdeye for OHLCV after we discovered the Birdeye free tier's
compute-unit budget exhausts in ~2 days of continuous operation. GeckoTerminal
is free, requires no API key, and serves historical 1m/1h/1d candles for any
tracked Solana pool.

Rate limit: ~30 calls/min on the free tier. We throttle to stay under.

Flow for our use:
    mint  --(DexScreener)-->  pool_address  --(GeckoTerminal)-->  OHLCV

API: https://www.geckoterminal.com/dex-api
  GET /networks/{network}/pools/{pool}/ohlcv/{timeframe}
      ?aggregate=1&limit=1000&before_timestamp={unix}
  Returns data.attributes.ohlcv_list = [[ts, o, h, l, c, vol], ...] (newest first)
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

import httpx

from helios.data.adapters.base import VenueError
from helios.ops import get_logger

log = get_logger(__name__)

GECKO_BASE = "https://api.geckoterminal.com/api/v2"
DEXSCREENER_TOKENS = "https://api.dexscreener.com/latest/dex/tokens"


class GeckoTerminalAdapter:
    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None,
        min_interval_seconds: float = 2.2,   # ~27/min, under the 30/min free cap
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=20.0,
            headers={"Accept": "application/json"},
        )
        self.min_interval_seconds = min_interval_seconds
        self._last_call = 0.0
        self._pool_cache: dict[str, Optional[str]] = {}

    async def _throttle(self) -> None:
        now = time.time()
        if now - self._last_call < self.min_interval_seconds:
            await asyncio.sleep(self.min_interval_seconds - (now - self._last_call))
        self._last_call = time.time()

    async def resolve_pool(self, mint: str) -> Optional[str]:
        """mint → most-liquid Solana pool address, via DexScreener. Cached."""
        if mint in self._pool_cache:
            return self._pool_cache[mint]
        try:
            resp = await self._client.get(f"{DEXSCREENER_TOKENS}/{mint}")
            resp.raise_for_status()
        except httpx.HTTPError:
            self._pool_cache[mint] = None
            return None
        pairs = [p for p in (resp.json().get("pairs") or []) if p.get("chainId") == "solana"]
        if not pairs:
            self._pool_cache[mint] = None
            return None
        best = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
        pool = best.get("pairAddress")
        self._pool_cache[mint] = pool
        return pool

    async def fetch_ohlcv_by_pool(
        self, pool: str, time_from: int, time_to: int, timeframe: str = "minute",
        aggregate: int = 1,
    ) -> list[dict]:
        """Fetch OHLCV candles for a pool within [time_from, time_to].

        GeckoTerminal returns up to 1000 candles ending at before_timestamp,
        newest-first. We page backward from time_to until we cover time_from.
        Output normalized to Birdeye-compatible dicts: {unixTime, o, h, l, c, v}.
        """
        all_rows: dict[int, dict] = {}
        cursor = time_to
        # Cap pages to avoid runaway; 1000 1m candles = ~16h per page
        for _ in range(20):
            if cursor <= time_from:
                break
            await self._throttle()
            params = {"aggregate": aggregate, "limit": 1000, "before_timestamp": cursor}
            try:
                resp = await self._client.get(
                    f"{GECKO_BASE}/networks/solana/pools/{pool}/ohlcv/{timeframe}",
                    params=params,
                )
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise VenueError(f"GeckoTerminal OHLCV failed for {pool}: {e}") from e
            ohlcv = (resp.json().get("data", {}).get("attributes", {}).get("ohlcv_list") or [])
            if not ohlcv:
                break
            oldest_in_page = ohlcv[-1][0]
            for row in ohlcv:
                ts = int(row[0])
                if ts < time_from:
                    continue
                all_rows[ts] = {
                    "unixTime": ts,
                    "o": float(row[1]), "h": float(row[2]),
                    "l": float(row[3]), "c": float(row[4]),
                    "v": float(row[5]),
                }
            if oldest_in_page >= cursor:
                break
            cursor = oldest_in_page
            if oldest_in_page <= time_from:
                break
        return [all_rows[t] for t in sorted(all_rows.keys())]

    async def fetch_ohlcv(
        self, mint: str, time_from: int, time_to: int, interval: str = "1m",
    ) -> list[dict]:
        """Birdeye-compatible signature: mint + unix range → candle dicts.
        Resolves the pool internally."""
        pool = await self.resolve_pool(mint)
        if not pool:
            return []
        tf_map = {"1m": ("minute", 1), "5m": ("minute", 5), "15m": ("minute", 15),
                  "1h": ("hour", 1), "1H": ("hour", 1), "1d": ("day", 1)}
        timeframe, aggregate = tf_map.get(interval, ("minute", 1))
        return await self.fetch_ohlcv_by_pool(pool, time_from, time_to, timeframe, aggregate)

    async def close(self) -> None:
        await self._client.aclose()
