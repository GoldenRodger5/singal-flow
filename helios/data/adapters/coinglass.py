"""Coinglass adapter — aggregated crypto perp liquidation & OI data.

Coinglass aggregates open-interest and liquidation history across major perp
venues (Binance, Bybit, OKX, Hyperliquid, dYdX, etc.) — including the ones US
residents cannot legally trade. The signal value is global; we trade the
correlated Kraken Futures perp.

Free tier (no auth): https://open-api-v4.coinglass.com/
  GET /api/futures/liquidation/aggregated-history?symbol=BTC
  GET /api/futures/open-interest/aggregated-history?symbol=BTC
  GET /api/futures/liquidation/heatmap/aggregated?symbol=BTC

Caveat: free tier rate-limited tightly. Use cautious polling (30s+).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import httpx

from helios.data.adapters.base import VenueError
from helios.ops import get_logger

log = get_logger(__name__)

COINGLASS_BASE = "https://open-api-v4.coinglass.com/api"


@dataclass(frozen=True, slots=True)
class LiquidationBucket:
    """One row of the liquidation history."""
    unix_time: int
    longs_liq_usd: float
    shorts_liq_usd: float

    @property
    def total_usd(self) -> float:
        return self.longs_liq_usd + self.shorts_liq_usd


@dataclass(frozen=True, slots=True)
class LiquidationHeatmapPoint:
    """One bin from the liquidation-level heatmap."""
    price_level: float
    liquidation_volume_usd: float
    side: str  # "long" or "short"


class CoinglassAdapter:
    """Public Coinglass v4 endpoints. Free tier, no auth, polite throttling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        min_interval_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("COINGLASS_API_KEY")  # optional; some endpoints need it
        self._client = client or httpx.AsyncClient(timeout=20.0)
        self.min_interval_seconds = min_interval_seconds
        self._last_call_ts: float = 0.0

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        # Simple throttle so the free tier doesn't 429 us
        import asyncio
        import time
        now = time.time()
        if now - self._last_call_ts < self.min_interval_seconds:
            await asyncio.sleep(self.min_interval_seconds - (now - self._last_call_ts))
        headers = {}
        if self.api_key:
            headers["CG-API-KEY"] = self.api_key
        try:
            resp = await self._client.get(f"{COINGLASS_BASE}{path}", params=params, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise VenueError(f"Coinglass {path} failed: {e}") from e
        finally:
            self._last_call_ts = time.time()
        body = resp.json()
        if str(body.get("code", "0")) not in ("0", "200"):
            raise VenueError(f"Coinglass error: {body.get('msg', body)!r}")
        return body

    async def fetch_liquidation_history(
        self, symbol: str, time_type: str = "5m", limit: int = 60,
    ) -> list[LiquidationBucket]:
        """Aggregated longs+shorts liquidation buckets. 5-minute bins by default.

        symbol: "BTC", "ETH", "SOL", etc. (NOT the perp pair name)
        time_type: "1m" "5m" "15m" "1h" "4h" "12h" "1d"
        limit: max 1000
        """
        body = await self._get(
            "/futures/liquidation/aggregated-history",
            params={"symbol": symbol, "time_type": time_type, "limit": limit},
        )
        rows = body.get("data") or []
        out: list[LiquidationBucket] = []
        for r in rows:
            out.append(LiquidationBucket(
                unix_time=int(r.get("t") or r.get("time") or 0),
                longs_liq_usd=float(r.get("longLiquidationUsd") or r.get("longs") or 0),
                shorts_liq_usd=float(r.get("shortLiquidationUsd") or r.get("shorts") or 0),
            ))
        return out

    async def fetch_liquidation_heatmap(self, symbol: str) -> list[LiquidationHeatmapPoint]:
        """Liquidation-level heatmap: where are the walls?

        Premium-tier on Coinglass; fallback to estimate-from-OI if unavailable.
        For free-tier users we return [] and the detector falls back to
        bucketing OI by recent price/leverage instead.
        """
        try:
            body = await self._get(
                "/futures/liquidation/heatmap/aggregated",
                params={"symbol": symbol, "time_type": "1h"},
            )
        except VenueError:
            return []  # premium endpoint, free tier may 403
        rows = (body.get("data") or {}).get("liquidations") or []
        out: list[LiquidationHeatmapPoint] = []
        for r in rows:
            try:
                out.append(LiquidationHeatmapPoint(
                    price_level=float(r.get("price", 0)),
                    liquidation_volume_usd=float(r.get("usd", 0)),
                    side=str(r.get("side", "long")),
                ))
            except (TypeError, ValueError):
                continue
        return out

    async def fetch_open_interest(self, symbol: str) -> float:
        """Aggregated open interest in USD."""
        body = await self._get(
            "/futures/open-interest/exchange-list",
            params={"symbol": symbol},
        )
        data = body.get("data") or []
        return float(sum(float(d.get("openInterestUsd", 0)) for d in data))

    async def close(self) -> None:
        await self._client.aclose()
