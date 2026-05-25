"""Birdeye adapter — Solana holder concentration data.

Free-tier endpoints we use:
  /defi/v3/token/holder   top holders with amounts (used for top-10 concentration)
  /defi/price             current USD price (kept as a sanity cross-check vs DexScreener)

Free tier does NOT include /defi/token_security (which would have given us mint
authority + LP-lock state in one call). We pull those from Helius RPC instead.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import httpx

from helios.data.adapters.base import VenueError
from helios.ops import get_logger

log = get_logger(__name__)

BIRDEYE_BASE = "https://public-api.birdeye.so"


@dataclass(frozen=True, slots=True)
class HolderStats:
    top_1_pct: float
    top_10_pct: float
    n_holders_reported: int  # may be capped by the limit we request


class BirdeyeAdapter:
    """Free-tier Birdeye client. Includes 429-aware exponential backoff."""

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
        max_retries: int = 5,
        base_backoff_seconds: float = 1.5,
    ) -> None:
        self.api_key = api_key or os.getenv("BIRDEYE_API_KEY")
        if not self.api_key:
            raise ValueError("BIRDEYE_API_KEY env var or api_key argument required")
        self._client = client or httpx.AsyncClient(
            timeout=20.0,
            headers={"X-API-KEY": self.api_key, "x-chain": "solana"},
        )
        self._max_retries = max_retries
        self._base_backoff = base_backoff_seconds

    async def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        """GET with 429 / 5xx backoff. Raises VenueError on persistent failure."""
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                resp = await self._client.get(url, params=params)
            except httpx.HTTPError as e:
                last_exc = e
                await asyncio.sleep(self._base_backoff * (2 ** attempt))
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = self._base_backoff * (2 ** attempt)
                # Honor Retry-After if present
                ra = resp.headers.get("Retry-After")
                if ra:
                    try:
                        wait = max(wait, float(ra))
                    except ValueError:
                        pass
                await asyncio.sleep(wait)
                continue
            return resp
        raise VenueError(f"Birdeye GET {url} failed after {self._max_retries} retries: {last_exc}")

    async def get_holder_stats(self, mint_address: str, limit: int = 20) -> HolderStats:
        """Top-N holders by ui_amount. We compute concentration relative to
        the sum of returned amounts as a stand-in for circulating supply
        (Birdeye's holder endpoint returns sorted-descending wallets)."""
        url = f"{BIRDEYE_BASE}/defi/v3/token/holder"
        try:
            resp = await self._get(url, params={"address": mint_address, "limit": limit})
            resp.raise_for_status()
        except (httpx.HTTPError, VenueError) as e:
            raise VenueError(f"Birdeye holder fetch failed for {mint_address}: {e}") from e
        body = resp.json()
        if not body.get("success", True):
            raise VenueError(f"Birdeye holder error: {body.get('message')!r}")
        items = (body.get("data") or {}).get("items") or []
        if not items:
            return HolderStats(top_1_pct=1.0, top_10_pct=1.0, n_holders_reported=0)

        # Use mint supply (from the first item's decimals) and the supply
        # endpoint elsewhere. For now compute concentration as fraction of
        # returned amounts (top-N over top-N is meaningless), so we ALSO need
        # total supply — fetched separately and passed in by the enricher.
        # Here we just return the raw amounts; the enricher does the math.
        amounts = [float(item.get("ui_amount", 0) or 0) for item in items]
        total_returned = sum(amounts) or 1.0
        top_1 = amounts[0] / total_returned if amounts else 0.0
        top_10 = sum(amounts[:10]) / total_returned if amounts else 0.0
        return HolderStats(
            top_1_pct=top_1,
            top_10_pct=top_10,
            n_holders_reported=len(items),
        )

    async def get_holder_concentration_vs_supply(
        self, mint_address: str, ui_supply: float, limit: int = 20,
    ) -> tuple[float, float, int]:
        """Top-1 and top-10 concentration as fraction of circulating ui_supply.
        Returns (top_1_pct, top_10_pct, n_returned)."""
        url = f"{BIRDEYE_BASE}/defi/v3/token/holder"
        resp = await self._get(url, params={"address": mint_address, "limit": limit})
        resp.raise_for_status()
        body = resp.json()
        if not body.get("success", True):
            raise VenueError(f"Birdeye holder error: {body.get('message')!r}")
        items = (body.get("data") or {}).get("items") or []
        if not items or ui_supply <= 0:
            return (1.0, 1.0, len(items))
        amounts = sorted([float(item.get("ui_amount", 0) or 0) for item in items], reverse=True)
        top_1 = amounts[0] / ui_supply if amounts else 1.0
        top_10 = sum(amounts[:10]) / ui_supply if amounts else 1.0
        # Clamp to [0, 1] — float drift can produce 1.0000001
        top_1 = min(max(top_1, 0.0), 1.0)
        top_10 = min(max(top_10, 0.0), 1.0)
        return (top_1, top_10, len(items))

    async def fetch_ohlcv(
        self,
        mint_address: str,
        time_from: int,
        time_to: int,
        interval: str = "1m",
    ) -> list[dict]:
        """Hourly/minute OHLCV for a Solana token, between unix timestamps.

        Returns a list of dicts: {unixTime, o, h, l, c, v, type}.
        Chunks the request if the window is large (Birdeye caps response size).

        interval: '1m', '3m', '5m', '15m', '30m', '1H', '2H', '4H', '6H', '8H',
                  '12H', '1D', '3D', '1W', '1M' per Birdeye docs.
        """
        url = f"{BIRDEYE_BASE}/defi/ohlcv"
        # Birdeye caps at ~1000 candles per response. Compute approximate chunk size.
        seconds_per_candle = {
            "1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800,
            "1H": 3600, "2H": 7200, "4H": 14400, "6H": 21600, "8H": 28800,
            "12H": 43200, "1D": 86400,
        }.get(interval, 60)
        chunk_seconds = 900 * seconds_per_candle

        all_items: list[dict] = []
        seen_times: set[int] = set()
        cursor = time_from
        while cursor < time_to:
            chunk_to = min(time_to, cursor + chunk_seconds)
            params = {
                "address": mint_address,
                "type": interval,
                "time_from": cursor,
                "time_to": chunk_to,
            }
            try:
                resp = await self._get(url, params=params)
                resp.raise_for_status()
            except (httpx.HTTPError, VenueError) as e:
                raise VenueError(f"Birdeye OHLCV failed for {mint_address}: {e}") from e
            body = resp.json()
            if not body.get("success", True):
                raise VenueError(f"Birdeye OHLCV error: {body.get('message')!r}")
            items = (body.get("data") or {}).get("items") or []
            new = 0
            for it in items:
                t = int(it.get("unixTime", 0))
                if t and t not in seen_times:
                    seen_times.add(t)
                    all_items.append(it)
                    new += 1
            cursor = chunk_to
            if not new:
                # No data in this chunk; keep moving forward
                pass
            # Be polite between chunks even when responses succeed
            await asyncio.sleep(0.4)
        all_items.sort(key=lambda i: i["unixTime"])
        return all_items

    async def close(self) -> None:
        await self._client.aclose()
