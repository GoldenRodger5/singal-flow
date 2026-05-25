"""X (Twitter) recent-search adapter — for crypto mention scraping.

API: https://docs.x.com/x-api/posts/search-posts-recent
Free tier: 100 reads/month per app at the time of writing — extremely tight.
Basic tier ($100/mo): 60k reads/month — viable for production.

For A5 shadow mode we use the free tier sparingly: poll once per 5 min for
the most-discussed crypto tickers. Even at 1 call per 5 min × 30 days × 24h
= 8640 calls/month, that's way over the free tier. So:
  - v1 free tier: poll every 60 min, scrape top 20 tickers — ~720 calls/month
  - v1 if user upgrades to Basic: poll every 60s, full firehose

If no X_API_BEARER is set, this adapter falls back to gracefully emitting an
empty stream so the rest of A5 can run on Farcaster/Reddit alone.

Usage:
    async with XSearchAdapter() as x:
        async for mention in x.stream_ticker_mentions(["BTC", "SOL", "WIF"]):
            detector.ingest_mention(mention)
"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Optional

import httpx

from helios.ops import get_logger
from helios.strategies.a5_sentiment.detector import MentionEvent

log = get_logger(__name__)

X_API_BASE = "https://api.twitter.com/2"


class XSearchAdapter:
    """Poll X for recent ticker mentions. Free-tier compatible."""

    def __init__(
        self,
        bearer: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        poll_interval_seconds: float = 3600.0,    # 1 hour for free tier
    ) -> None:
        self.bearer = bearer or os.getenv("X_API_BEARER")
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self.poll_interval_seconds = poll_interval_seconds

    async def __aenter__(self) -> "XSearchAdapter":
        return self

    async def __aexit__(self, *exc) -> None:
        await self._client.aclose()

    async def stream_ticker_mentions(self, tickers: list[str]) -> AsyncIterator[MentionEvent]:
        """Yield MentionEvent objects for each ticker mention. Polls forever.

        If no bearer token, yields nothing (silent passthrough).
        """
        if not self.bearer:
            log.info("x_adapter_disabled_no_bearer")
            # Yield nothing, but keep the iterator alive so callers don't crash.
            while True:
                await asyncio.sleep(3600)
                # never yields. This is intentional — A5 can survive without X.
                if False:
                    yield  # type: ignore[unreachable]

        seen_tweet_ids: set[str] = set()

        while True:
            for ticker in tickers:
                try:
                    async for mention in self._search_ticker(ticker, seen_tweet_ids):
                        yield mention
                except Exception as e:  # noqa: BLE001
                    log.warning("x_search_failed", ticker=ticker, error=str(e))
            await asyncio.sleep(self.poll_interval_seconds)

    async def _search_ticker(self, ticker: str, seen: set[str]) -> AsyncIterator[MentionEvent]:
        # Query: $TICKER OR #TICKER. Exclude retweets.
        query = f"(${ticker} OR #{ticker}) -is:retweet"
        params = {
            "query": query,
            "max_results": 100,
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "public_metrics",
        }
        try:
            resp = await self._client.get(
                f"{X_API_BASE}/tweets/search/recent",
                params=params,
                headers={"Authorization": f"Bearer {self.bearer}"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("x_request_failed", ticker=ticker, error=str(e))
            return
        body = resp.json()
        tweets = body.get("data") or []
        users = {u["id"]: u for u in (body.get("includes", {}).get("users") or [])}

        for t in tweets:
            tid = t.get("id")
            if not tid or tid in seen:
                continue
            seen.add(tid)
            created = t.get("created_at")
            try:
                ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except (TypeError, AttributeError, ValueError):
                ts = datetime.now(timezone.utc)
            author = users.get(t.get("author_id", ""), {})
            metrics = author.get("public_metrics") or {}
            followers = int(metrics.get("followers_count", 0) or 0)
            # Weight scheme: low-follower accounts heavily discounted.
            weight = 0.1
            if followers >= 1000:
                weight = 1.0
            if followers >= 50_000:
                weight = 3.0
            if followers >= 500_000:
                weight = 8.0
            yield MentionEvent(
                ticker=ticker,
                source="x",
                timestamp=ts,
                weight=weight,
                sentiment=0.0,  # could run a quick model here; skip in v1
            )
