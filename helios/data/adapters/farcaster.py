"""Farcaster mention adapter — uses the public Neynar / Warpcast API.

Farcaster is a decentralized social protocol. Public endpoint:
  https://api.warpcast.com/v2/recent-casts   (no auth required for read)
  https://api.neynar.com/v2/farcaster/feed/  (auth, free dev tier)

For v1 we use the public Warpcast endpoint. If NEYNAR_API_KEY is set, we
use Neynar's more powerful search endpoint instead.

Lower volume than X but: less noise, more crypto-native, free.
"""
from __future__ import annotations

import asyncio
import os
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Optional

import httpx

from helios.ops import get_logger
from helios.strategies.a5_sentiment.detector import MentionEvent

log = get_logger(__name__)

WARPCAST_BASE = "https://api.warpcast.com/v2"
NEYNAR_BASE = "https://api.neynar.com/v2"

# $TICKER or #TICKER followed by a word boundary
TICKER_PATTERN = re.compile(r"[$#]([A-Z]{2,12})\b")


class FarcasterAdapter:
    def __init__(
        self,
        neynar_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        poll_interval_seconds: float = 120.0,
    ) -> None:
        self.neynar_key = neynar_key or os.getenv("NEYNAR_API_KEY")
        self._client = client or httpx.AsyncClient(timeout=20.0)
        self.poll_interval_seconds = poll_interval_seconds

    async def stream_ticker_mentions(self, tickers: list[str] | None = None) -> AsyncIterator[MentionEvent]:
        """Poll recent casts, extract $TICKER mentions, yield MentionEvent.

        If `tickers` is None, emits every ticker found. If supplied, only emits
        mentions for tickers in the list (uppercased, no leading $).
        """
        ticker_set = {t.upper().lstrip("$") for t in (tickers or [])}
        seen_hashes: set[str] = set()

        while True:
            try:
                casts = await self._fetch_recent_casts()
            except Exception as e:  # noqa: BLE001
                log.warning("farcaster_fetch_failed", error=str(e))
                await asyncio.sleep(self.poll_interval_seconds)
                continue

            for cast in casts:
                cast_hash = cast.get("hash") or cast.get("hash_id")
                if not cast_hash or cast_hash in seen_hashes:
                    continue
                seen_hashes.add(cast_hash)
                text = cast.get("text") or ""
                ts_str = cast.get("timestamp") or cast.get("created_at") or ""
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except (TypeError, ValueError):
                    ts = datetime.now(timezone.utc)
                # Weight scheme: by follower count of author if available
                author = cast.get("author") or {}
                followers = int((author.get("follower_count") or 0) or 0)
                weight = 0.5 if followers < 500 else 1.0
                if followers >= 10_000:
                    weight = 3.0
                for match in TICKER_PATTERN.finditer(text.upper()):
                    ticker = match.group(1)
                    if ticker_set and ticker not in ticker_set:
                        continue
                    yield MentionEvent(
                        ticker=ticker, source="farcaster",
                        timestamp=ts, weight=weight,
                    )

            await asyncio.sleep(self.poll_interval_seconds)

    async def _fetch_recent_casts(self) -> list[dict]:
        if self.neynar_key:
            # Neynar trending feed — best signal, requires auth
            resp = await self._client.get(
                f"{NEYNAR_BASE}/farcaster/feed/trending",
                params={"time_window": "1h", "limit": 100},
                headers={"api_key": self.neynar_key, "x-api-key": self.neynar_key},
            )
            resp.raise_for_status()
            return (resp.json().get("casts") or [])
        # Fallback: Warpcast public recent-casts (no auth)
        resp = await self._client.get(f"{WARPCAST_BASE}/recent-casts", params={"limit": 100})
        resp.raise_for_status()
        body = resp.json()
        return (body.get("result", {}).get("casts") or [])

    async def close(self) -> None:
        await self._client.aclose()
