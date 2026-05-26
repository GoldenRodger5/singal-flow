"""A5 outcome harvester — measure realized P&L of sentiment-velocity signals.

For each sentiment signal logged:
  1. Resolve the ticker symbol → the Solana mint address with deepest liquidity
     via DexScreener's search endpoint. (Public, no auth.)
  2. Fetch Birdeye 1-minute OHLCV from signal_time → signal_time + N hours.
  3. Simulate a trade: enter at signal_time, exit at first of target / stop / time.
  4. Write outcome to a5_outcomes.jsonl.

The ticker-to-mint resolution is the tricky part. Many tickers collide
(WIF = "dogwifhat" on Solana but a different WIF might exist on other chains).
We use DexScreener's `/dex/search?q=$WIF` and pick the Solana pair with the
highest liquidity. We cache the resolution per ticker so we don't re-call
DexScreener every harvest cycle.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx

from helios.data.adapters.birdeye import BirdeyeAdapter
from helios.ops import get_logger

log = get_logger(__name__)

A5_SHADOW_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a5_shadow.jsonl"
A5_OUTCOMES_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a5_outcomes.jsonl"
A5_TICKER_CACHE = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a5_ticker_to_mint.json"

OUTCOME_WINDOW_HOURS = 4
MIN_WINDOW_HOURS = 2
TARGET_MULT = 2.0      # 100% gain target
STOP_PCT = 0.30        # 30% drawdown stop


@dataclass(frozen=True, slots=True)
class SentimentOutcome:
    signal_timestamp_iso: str
    ticker: str
    resolved_mint: Optional[str]
    entry_price: float
    target_price: float
    stop_price: float
    exit_reason: str
    exit_price: float
    realized_return_pct: float
    held_minutes: int


class _TickerCache:
    """Disk-backed ticker → mint resolution cache."""

    def __init__(self, path: Path = A5_TICKER_CACHE) -> None:
        self.path = path
        self._cache: dict[str, str] = {}
        if path.exists():
            try:
                self._cache = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                self._cache = {}

    def get(self, ticker: str) -> Optional[str]:
        return self._cache.get(ticker.upper())

    def set(self, ticker: str, mint: str) -> None:
        self._cache[ticker.upper()] = mint
        parent = self.path.parent
        target = parent.resolve() if parent.is_symlink() else parent
        try:
            target.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
        self.path.write_text(json.dumps(self._cache))


async def _resolve_ticker_to_mint(
    ticker: str, client: httpx.AsyncClient, cache: _TickerCache,
) -> Optional[str]:
    """Look up the Solana mint with the deepest liquidity for a given ticker."""
    cached = cache.get(ticker)
    if cached:
        return cached
    try:
        resp = await client.get(
            "https://api.dexscreener.com/latest/dex/search",
            params={"q": f"${ticker}"},
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("dex_search_failed", ticker=ticker, error=str(e))
        return None
    pairs = (resp.json() or {}).get("pairs") or []
    sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
    if not sol_pairs:
        return None
    # Pick by liquidity desc; symbol must match (case-insensitive)
    sol_pairs = [
        p for p in sol_pairs
        if (p.get("baseToken", {}).get("symbol", "") or "").upper() == ticker.upper()
    ]
    if not sol_pairs:
        return None
    best = max(sol_pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
    mint = best.get("baseToken", {}).get("address")
    if mint:
        cache.set(ticker, mint)
    return mint


def _key_of(record: dict) -> str:
    sig = record.get("signal") or {}
    return f"{record.get('timestamp_iso','')}|{sig.get('ticker', record.get('ticker',''))}"


def _read_existing(path: Path = A5_OUTCOMES_PATH) -> set[str]:
    if not path.exists():
        return set()
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                seen.add(f"{rec.get('signal_timestamp_iso','')}|{rec.get('ticker','')}")
            except json.JSONDecodeError:
                continue
    return seen


def _write(rec: dict, path: Path = A5_OUTCOMES_PATH) -> None:
    parent = path.parent
    target = parent.resolve() if parent.is_symlink() else parent
    try:
        target.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def _simulate(candles: list[dict], entry_price: float) -> SentimentOutcome | None:
    """Simulate a long entry at candles[0] open, target/stop/time-based exit."""
    if not candles or entry_price <= 0:
        return None
    target_price = entry_price * TARGET_MULT
    stop_price = entry_price * (1.0 - STOP_PCT)

    exit_reason = "time"
    exit_price = float(candles[-1].get("c", entry_price))
    held_minutes = len(candles)

    for i, c in enumerate(candles):
        h = float(c.get("h", 0))
        l = float(c.get("l", 0))
        if l <= stop_price:
            exit_reason = "stop"
            exit_price = stop_price
            held_minutes = i + 1
            break
        if h >= target_price:
            exit_reason = "target"
            exit_price = target_price
            held_minutes = i + 1
            break
    realized = (exit_price - entry_price) / entry_price
    return SentimentOutcome(
        signal_timestamp_iso="",  # caller fills
        ticker="",                # caller fills
        resolved_mint=None,
        entry_price=entry_price,
        target_price=target_price,
        stop_price=stop_price,
        exit_reason=exit_reason,
        exit_price=exit_price,
        realized_return_pct=realized,
        held_minutes=held_minutes,
    )


async def harvest_a5(
    shadow_path: Path = A5_SHADOW_PATH,
    outcomes_path: Path = A5_OUTCOMES_PATH,
    birdeye: Optional[BirdeyeAdapter] = None,
    window_hours: int = OUTCOME_WINDOW_HOURS,
) -> dict[str, int]:
    if not shadow_path.exists():
        return {"processed": 0, "skipped_recent": 0, "skipped_done": 0,
                "skipped_no_mint": 0, "failed": 0}

    own_birdeye = birdeye is None
    birdeye = birdeye or BirdeyeAdapter()
    cache = _TickerCache()
    seen = _read_existing(outcomes_path)
    counts = {"processed": 0, "skipped_recent": 0, "skipped_done": 0,
              "skipped_no_mint": 0, "failed": 0}
    now = datetime.now(timezone.utc)

    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            with shadow_path.open("r", encoding="utf-8") as f:
                rows = [json.loads(line) for line in f if line.strip()]

            for rec in rows:
                key = _key_of(rec)
                if key in seen:
                    counts["skipped_done"] += 1
                    continue
                signal = rec.get("signal") or {}
                if not signal:
                    continue
                ticker = (signal.get("ticker") or rec.get("ticker", "")).upper().lstrip("$")
                if not ticker:
                    continue
                try:
                    sig_time = datetime.fromisoformat(rec["timestamp_iso"])
                except (ValueError, KeyError):
                    counts["failed"] += 1
                    continue
                if (now - sig_time).total_seconds() < MIN_WINDOW_HOURS * 3600:
                    counts["skipped_recent"] += 1
                    continue

                mint = await _resolve_ticker_to_mint(ticker, http, cache)
                if not mint:
                    counts["skipped_no_mint"] += 1
                    continue

                # Fetch 1-min OHLCV signal_time → signal_time + window
                from_ts = int(sig_time.timestamp())
                to_ts = int(min(now, sig_time + timedelta(hours=window_hours)).timestamp())
                try:
                    raw = await birdeye.fetch_ohlcv(mint, from_ts, to_ts, interval="1m")
                except Exception as e:  # noqa: BLE001
                    log.warning("a5_harvest_ohlcv_failed", ticker=ticker, mint=mint, error=str(e))
                    counts["failed"] += 1
                    continue
                if not raw:
                    counts["failed"] += 1
                    continue
                entry_price = float(raw[0].get("o", 0))
                outcome = _simulate(raw, entry_price)
                if outcome is None:
                    counts["failed"] += 1
                    continue
                rec_out = {
                    **outcome.__dict__,
                    "signal_timestamp_iso": rec["timestamp_iso"],
                    "ticker": ticker,
                    "resolved_mint": mint,
                    "z_score_at_signal": signal.get("z_score"),
                    "mentions_per_min_at_signal": signal.get("mentions_last_minute"),
                    "harvested_iso": now.isoformat(),
                }
                _write(rec_out, outcomes_path)
                counts["processed"] += 1
                seen.add(key)
    finally:
        if own_birdeye:
            await birdeye.close()
    return counts


async def harvest_loop(interval_minutes: float = 60.0) -> None:
    log.info("a5_harvest_loop_starting", interval_minutes=interval_minutes)
    while True:
        try:
            counts = await harvest_a5()
            log.info("a5_harvest_tick", **counts)
        except Exception as e:  # noqa: BLE001
            log.warning("a5_harvest_failed", error=str(e))
        await asyncio.sleep(interval_minutes * 60.0)
