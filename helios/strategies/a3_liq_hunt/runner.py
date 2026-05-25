"""A3 shadow runner — polls Coinglass + Kraken Futures, runs the detector,
logs would-have-traded signals to JSONL for outcome harvest later.

Mirrors the A2 shadow runner pattern but for a completely different mechanism
(liquidation cluster fading/riding instead of token launch sniping). Both run
in parallel feeding the same outcome-analysis pipeline.
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

from helios.data.adapters.coinglass import CoinglassAdapter
from helios.data.adapters.kraken_futures import KrakenFuturesMarketData
from helios.ops import get_logger
from helios.strategies.a3_liq_hunt.detector import (
    CascadeSignal,
    LiquidationDetector,
)

log = get_logger(__name__)

A3_LOG_DEFAULT = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a3_shadow.jsonl"


def _write_record(record: dict, path: Path = A3_LOG_DEFAULT) -> None:
    parent = path.parent
    target = parent.resolve() if parent.is_symlink() else parent
    try:
        target.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


SYMBOLS_MAP = {
    "BTC": "PF_XBTUSD",
    "ETH": "PF_ETHUSD",
    "SOL": "PF_SOLUSD",
}


class A3ShadowRunner:
    def __init__(
        self,
        detector: Optional[LiquidationDetector] = None,
        coinglass: Optional[CoinglassAdapter] = None,
        kraken: Optional[KrakenFuturesMarketData] = None,
        symbols: tuple[str, ...] = ("BTC", "ETH", "SOL"),
        poll_interval_seconds: float = 60.0,
    ) -> None:
        self.detector = detector or LiquidationDetector()
        self.coinglass = coinglass or CoinglassAdapter()
        self.kraken = kraken or KrakenFuturesMarketData()
        self.symbols = symbols
        self.poll_interval_seconds = poll_interval_seconds

    async def run(self) -> None:
        log.info("a3_shadow_starting", symbols=list(self.symbols))
        try:
            iteration = 0
            while True:
                iteration += 1
                iter_start = time.time()
                for sym in self.symbols:
                    await self._evaluate_symbol(sym)
                dt = time.time() - iter_start
                iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
                print(f"[{iso}] a3 iter={iteration:>4d} dt={dt:.1f}s", flush=True)
                # Coinglass free tier is the binding throttle (30s+)
                await asyncio.sleep(max(1.0, self.poll_interval_seconds - dt))
        finally:
            await self.coinglass.close()
            await self.kraken.close()

    async def _evaluate_symbol(self, symbol: str) -> None:
        try:
            # Recent Kraken Futures 5-min bars to estimate current price + cascade detection
            from datetime import timedelta
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=2)
            kraken_sym = SYMBOLS_MAP.get(symbol, f"PF_{symbol}USD")
            bars = await self.kraken.fetch_bars(kraken_sym, "5m", start, end)
            if not bars:
                return
            current_price = float(bars[-1].close)

            # Liquidation history (last 60 of 5-min bins = 5h)
            liq_history = await self.coinglass.fetch_liquidation_history(symbol, time_type="5m", limit=60)
            recent_liqs = [(b.unix_time, b.total_usd) for b in liq_history[-12:]]  # last hour

            # Detect cascade
            recent_ohlc = [
                {"time": int(b.event_time.timestamp()), "o": float(b.open),
                 "h": float(b.high), "l": float(b.low), "c": float(b.close), "v": float(b.volume)}
                for b in bars[-24:]  # last 2h
            ]
            cascade = self.detector.detect_recent_cascade(symbol, recent_ohlc, recent_liqs)

            # Build leverage buckets from liquidation history → approximate the heatmap
            # For free tier we approximate: each historical liq bin contributed at the
            # midpoint price of that bar (which we estimate from kraken bars at the
            # same timestamp). This is a *rough* heatmap proxy.
            heatmap = await self.coinglass.fetch_liquidation_heatmap(symbol)
            if heatmap:
                leverage_buckets = [(p.price_level, p.liquidation_volume_usd) for p in heatmap]
            else:
                # Fallback: use recent liq sizes bucketed by recent bar lows/highs
                price_idx = {int(b.event_time.timestamp()): (float(b.low), float(b.high)) for b in bars}
                buckets: list[tuple[float, float]] = []
                for t, usd in recent_liqs:
                    if t in price_idx:
                        lo, hi = price_idx[t]
                        # Longs liquidated near bar low, shorts near bar high — without long/short split,
                        # split the volume evenly across the two extremes.
                        buckets.append((lo, usd / 2))
                        buckets.append((hi, usd / 2))
                leverage_buckets = buckets

            clusters = self.detector.detect_clusters(symbol, current_price, leverage_buckets)
            signal = self.detector.score_signal(current_price, clusters, cascade)

            # Always log the evaluation — even no-signal rows are useful for calibration
            record = {
                "timestamp_iso": datetime.now(timezone.utc).isoformat(),
                "symbol": symbol,
                "current_price": current_price,
                "n_clusters": len(clusters),
                "top_cluster": asdict(clusters[0]) if clusters else None,
                "cascade": asdict(cascade) if cascade else None,
                "signal": asdict(signal) if signal else None,
                "decision": "trade" if signal else "no_trade",
            }
            _write_record(record)
            if signal:
                log.info(
                    "a3_signal",
                    symbol=symbol, variant=signal.variant,
                    direction=signal.direction, confidence=f"{signal.confidence:.2f}",
                    target_pct=f"{signal.expected_target_pct:.2%}",
                )
        except Exception as e:  # noqa: BLE001
            log.warning("a3_eval_failed", symbol=symbol, error=str(e))
