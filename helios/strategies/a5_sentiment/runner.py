"""A5 shadow runner — ingest X + Farcaster mentions, run the detector,
log signals + outcomes for later harvest.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from helios.data.adapters.farcaster import FarcasterAdapter
from helios.data.adapters.x_search import XSearchAdapter
from helios.ops import get_logger
from helios.strategies.a5_sentiment.detector import SentimentDetector

log = get_logger(__name__)

A5_LOG_DEFAULT = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a5_shadow.jsonl"

# Tickers to watch. Mix of majors + active memecoins.
DEFAULT_WATCHLIST = (
    "BTC", "ETH", "SOL",
    "WIF", "POPCAT", "BONK", "MEW", "PNUT", "GOAT",
    "FARTCOIN", "AI16Z", "HYPE", "MELANIA",
)


def _write_record(record: dict, path: Path = A5_LOG_DEFAULT) -> None:
    parent = path.parent
    target = parent.resolve() if parent.is_symlink() else parent
    try:
        target.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


class A5ShadowRunner:
    def __init__(
        self,
        tickers: tuple[str, ...] = DEFAULT_WATCHLIST,
        detector: Optional[SentimentDetector] = None,
        x: Optional[XSearchAdapter] = None,
        farcaster: Optional[FarcasterAdapter] = None,
        evaluate_interval_seconds: float = 30.0,
    ) -> None:
        self.tickers = tickers
        self.detector = detector or SentimentDetector()
        self.x = x or XSearchAdapter()
        self.farcaster = farcaster or FarcasterAdapter()
        self.evaluate_interval = evaluate_interval_seconds

    async def run(self) -> None:
        log.info("a5_shadow_starting", tickers=list(self.tickers))

        ingest_x = asyncio.create_task(self._ingest_x())
        ingest_fc = asyncio.create_task(self._ingest_farcaster())
        evaluate = asyncio.create_task(self._evaluate_loop())

        try:
            await asyncio.gather(ingest_x, ingest_fc, evaluate)
        finally:
            for t in (ingest_x, ingest_fc, evaluate):
                t.cancel()

    async def _ingest_x(self) -> None:
        try:
            async with self.x as x:
                async for mention in x.stream_ticker_mentions(list(self.tickers)):
                    self.detector.ingest_mention(mention)
        except Exception as e:  # noqa: BLE001
            log.warning("a5_x_stream_died", error=str(e))

    async def _ingest_farcaster(self) -> None:
        try:
            async for mention in self.farcaster.stream_ticker_mentions(list(self.tickers)):
                self.detector.ingest_mention(mention)
        except Exception as e:  # noqa: BLE001
            log.warning("a5_farcaster_stream_died", error=str(e))

    async def _evaluate_loop(self) -> None:
        iteration = 0
        while True:
            iteration += 1
            now = datetime.now(timezone.utc)
            for ticker in self.tickers:
                sig = self.detector.evaluate(ticker, now=now)
                if sig is not None:
                    record = {
                        "timestamp_iso": now.isoformat(),
                        "ticker": sig.ticker,
                        "signal": asdict(sig),
                    }
                    _write_record(record)
                    log.info(
                        "a5_signal",
                        ticker=sig.ticker, z=f"{sig.z_score:.2f}",
                        mentions_per_min=f"{sig.mentions_last_minute:.1f}",
                        baseline=f"{sig.mentions_per_min_baseline:.2f}",
                        sources=sig.contributing_sources,
                    )
            await asyncio.sleep(self.evaluate_interval)
