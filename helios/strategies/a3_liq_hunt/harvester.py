"""A3 outcome harvester — measure realized P&L of past cascade signals.

For each row in a3_shadow.jsonl with signal != None:
  1. Fetch Kraken Futures 5-minute bars from signal time → signal time + N hours
  2. Simulate the trade: enter at signal_time close, exit at first of
     [target hit, stop hit, time-window end]
  3. Compute realized return as R-multiple (R = stop distance)
  4. Write to a3_outcomes.jsonl

Idempotent: skips signals already in a3_outcomes.jsonl by their (timestamp, symbol)
key. Safe to re-run.
"""
from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from helios.data.adapters.kraken_futures import KrakenFuturesMarketData
from helios.ops import get_logger

log = get_logger(__name__)

A3_SHADOW_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a3_shadow.jsonl"
A3_OUTCOMES_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a3_outcomes.jsonl"

# Kraken symbol map matches A3 runner
SYMBOLS_MAP = {
    "BTC": "PF_XBTUSD",
    "ETH": "PF_ETHUSD",
    "SOL": "PF_SOLUSD",
}

# Outcome windows
OUTCOME_WINDOW_HOURS = 4
MIN_WINDOW_HOURS = 2  # only harvest signals at least 2h old (need post-trade data)


@dataclass(frozen=True, slots=True)
class CascadeOutcome:
    signal_timestamp_iso: str
    symbol: str
    variant: str
    direction: int                # +1 long, -1 short
    entry_price: float
    target_price: float
    stop_price: float
    exit_reason: str              # "target" | "stop" | "time"
    exit_price: float
    realized_r_multiple: float    # P&L in R-multiples (1R = stop distance)
    held_minutes: int


def _key_of(record: dict) -> str:
    return f"{record.get('timestamp_iso','')}|{record.get('symbol','')}"


def _read_existing_outcomes(path: Path = A3_OUTCOMES_PATH) -> set[str]:
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
                seen.add(f"{rec.get('signal_timestamp_iso','')}|{rec.get('symbol','')}")
            except json.JSONDecodeError:
                continue
    return seen


def _write_outcome(rec: dict, path: Path = A3_OUTCOMES_PATH) -> None:
    parent = path.parent
    target = parent.resolve() if parent.is_symlink() else parent
    try:
        target.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def _simulate_outcome(
    bars: list, signal: dict, current_price: float, symbol: str, signal_time_iso: str,
) -> Optional[CascadeOutcome]:
    """Simulate the trade given 5m Kraken bars after the signal."""
    direction = int(signal.get("direction", 0))
    expected_target_pct = float(signal.get("expected_target_pct", 0.0))
    invalidation_price = float(signal.get("invalidation_price", 0.0))
    if direction == 0 or invalidation_price <= 0 or current_price <= 0:
        return None
    target_price = current_price * (1.0 + expected_target_pct * direction)
    # 1R = distance from entry to invalidation
    stop_distance_pct = abs(current_price - invalidation_price) / max(current_price, 1.0)
    if stop_distance_pct == 0:
        return None
    target_distance_pct = expected_target_pct

    exit_reason = "time"
    exit_price = float(bars[-1].close) if bars else current_price
    held_minutes = OUTCOME_WINDOW_HOURS * 60

    for i, bar in enumerate(bars):
        high = float(bar.high)
        low = float(bar.low)
        # Conservative tie-break: assume stop fires before target if both hit
        if direction == 1:
            if low <= invalidation_price:
                exit_reason = "stop"
                exit_price = invalidation_price
                held_minutes = (i + 1) * 5
                break
            if high >= target_price:
                exit_reason = "target"
                exit_price = target_price
                held_minutes = (i + 1) * 5
                break
        else:  # short
            if high >= invalidation_price:
                exit_reason = "stop"
                exit_price = invalidation_price
                held_minutes = (i + 1) * 5
                break
            if low <= target_price:
                exit_reason = "target"
                exit_price = target_price
                held_minutes = (i + 1) * 5
                break

    if direction == 1:
        realized_pct = (exit_price - current_price) / current_price
    else:
        realized_pct = (current_price - exit_price) / current_price
    realized_r = realized_pct / stop_distance_pct

    return CascadeOutcome(
        signal_timestamp_iso=signal_time_iso,
        symbol=symbol,
        variant=str(signal.get("variant", "")),
        direction=direction,
        entry_price=current_price,
        target_price=target_price,
        stop_price=invalidation_price,
        exit_reason=exit_reason,
        exit_price=exit_price,
        realized_r_multiple=realized_r,
        held_minutes=held_minutes,
    )


async def harvest_a3(
    shadow_path: Path = A3_SHADOW_PATH,
    outcomes_path: Path = A3_OUTCOMES_PATH,
    kraken: Optional[KrakenFuturesMarketData] = None,
    window_hours: int = OUTCOME_WINDOW_HOURS,
) -> dict[str, int]:
    """Walk a3_shadow.jsonl, harvest matured signal outcomes. Idempotent."""
    if not shadow_path.exists():
        return {"processed": 0, "skipped_recent": 0, "skipped_no_signal": 0,
                "skipped_done": 0, "failed": 0}

    own_kraken = kraken is None
    kraken = kraken or KrakenFuturesMarketData()
    seen = _read_existing_outcomes(outcomes_path)
    counts = {"processed": 0, "skipped_recent": 0, "skipped_no_signal": 0,
              "skipped_done": 0, "failed": 0}
    now = datetime.now(timezone.utc)

    try:
        with shadow_path.open("r", encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]

        for rec in rows:
            key = _key_of(rec)
            if key in seen:
                counts["skipped_done"] += 1
                continue
            signal = rec.get("signal")
            if not signal:
                counts["skipped_no_signal"] += 1
                continue
            try:
                signal_time = datetime.fromisoformat(rec["timestamp_iso"])
            except (ValueError, KeyError):
                counts["failed"] += 1
                continue
            if (now - signal_time).total_seconds() < MIN_WINDOW_HOURS * 3600:
                counts["skipped_recent"] += 1
                continue

            symbol = rec.get("symbol", "")
            kraken_sym = SYMBOLS_MAP.get(symbol, f"PF_{symbol}USD")
            current_price = float(rec.get("current_price", 0))
            try:
                bars = await kraken.fetch_bars(
                    kraken_sym, "5m",
                    signal_time,
                    min(now, signal_time + timedelta(hours=window_hours)),
                )
            except Exception as e:  # noqa: BLE001
                log.warning("a3_harvest_bars_failed", symbol=symbol, error=str(e))
                counts["failed"] += 1
                continue
            if not bars:
                counts["failed"] += 1
                continue

            outcome = _simulate_outcome(bars, signal, current_price, symbol, rec["timestamp_iso"])
            if outcome is None:
                counts["failed"] += 1
                continue
            _write_outcome({
                **outcome.__dict__,
                "harvested_iso": now.isoformat(),
            }, outcomes_path)
            counts["processed"] += 1
            seen.add(key)
    finally:
        if own_kraken:
            await kraken.close()
    return counts


async def harvest_loop(interval_minutes: float = 60.0) -> None:
    """Periodic harvest loop — designed to run as a supervised task."""
    log.info("a3_harvest_loop_starting", interval_minutes=interval_minutes)
    while True:
        try:
            counts = await harvest_a3()
            log.info("a3_harvest_tick", **counts)
        except Exception as e:  # noqa: BLE001
            log.warning("a3_harvest_failed", error=str(e))
        await asyncio.sleep(interval_minutes * 60.0)
