"""A2 token re-snapshot trail.

For every token logged in `a2_shadow.jsonl` in the last 24 hours, re-fetch its
DexScreener snapshot every N minutes. This gives us a TIME SERIES of token
state (liquidity, holders, txn count, price) — not just one point-in-time.

Why it matters:
  * Most rugs happen WITHIN the first 24 hours of detection.
  * Did liquidity drop 80% an hour after our snapshot? Useful label.
  * Did volume die to zero in 3 hours? Useful label.
  * Did the price 50x then crash 95%? Useful label.

Output: `a2_token_trail.jsonl` — one row per (mint, observation_time):
    {mint, t_offset_minutes, liquidity_usd, fdv_usd, txns_5m, price_usd, ...}

Idempotent: dedupes by (mint, t_offset_minutes_rounded) so repeat-runs are safe.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from helios.data.adapters.dexscreener import DexScreenerAdapter
from helios.ops import get_logger

log = get_logger(__name__)

A2_SHADOW_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a2_shadow.jsonl"
TRAIL_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a2_token_trail.jsonl"

RESNAP_INTERVAL_MINUTES = 60.0   # re-check each token every hour
MAX_AGE_HOURS = 24                # stop re-snapping after 24h


def _write(rec: dict, path: Path = TRAIL_PATH) -> None:
    parent = path.parent
    target = parent.resolve() if parent.is_symlink() else parent
    try:
        target.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def _read_existing(path: Path = TRAIL_PATH) -> set[str]:
    """Returns set of "{mint}|{t_offset_minutes_rounded}" already written."""
    if not path.exists():
        return set()
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                seen.add(f"{r.get('mint','')}|{int(r.get('t_offset_minutes',0))}")
            except json.JSONDecodeError:
                continue
    return seen


def _collect_tokens_to_resnap(
    shadow_path: Path = A2_SHADOW_PATH,
    max_age_hours: float = MAX_AGE_HOURS,
) -> list[tuple[str, datetime]]:
    """Return list of (mint, original_detection_time) for tokens detected
    within the last `max_age_hours`."""
    if not shadow_path.exists():
        return []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max_age_hours)
    result: dict[str, datetime] = {}  # mint -> earliest detection
    with shadow_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ts = datetime.fromisoformat(rec["timestamp_iso"])
                if ts < cutoff:
                    continue
                mint = rec.get("mint")
                if not mint:
                    continue
                if mint not in result or ts < result[mint]:
                    result[mint] = ts
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return list(result.items())


async def resnap_once(
    dex: Optional[DexScreenerAdapter] = None,
    shadow_path: Path = A2_SHADOW_PATH,
    trail_path: Path = TRAIL_PATH,
) -> dict[str, int]:
    """Single pass: for each token in the last 24h, fetch fresh DexScreener
    state and append to the trail file.
    """
    own_dex = dex is None
    dex = dex or DexScreenerAdapter()
    seen = _read_existing(trail_path)
    counts = {"resnapped": 0, "skipped_done": 0, "failed": 0, "no_data": 0}
    now = datetime.now(timezone.utc)

    try:
        tokens = _collect_tokens_to_resnap(shadow_path)
        for mint, detection_time in tokens:
            t_offset_minutes = int((now - detection_time).total_seconds() // 60)
            # Round to nearest hour for the dedup key (so re-runs within a
            # given hour don't double-write)
            t_offset_hour_key = f"{mint}|{(t_offset_minutes // 60) * 60}"
            if t_offset_hour_key in seen:
                counts["skipped_done"] += 1
                continue
            try:
                snap = await dex.fetch_token_snapshot(mint)
            except Exception as e:  # noqa: BLE001
                log.warning("resnap_failed", mint=mint, error=str(e))
                counts["failed"] += 1
                continue
            if snap is None:
                counts["no_data"] += 1
                continue
            _write({
                "mint": mint,
                "detection_timestamp_iso": detection_time.isoformat(),
                "resnap_timestamp_iso": now.isoformat(),
                "t_offset_minutes": t_offset_minutes,
                "liquidity_usd": str(snap.liquidity_usd),
                "fdv_usd": str(snap.fully_diluted_value_usd),
                "volume_5m_usd": str(snap.volume_5m_usd),
                "volume_1h_usd": str(snap.volume_1h_usd),
                "txns_5m": snap.txns_5m,
                "txns_1h": snap.txns_1h,
                "price_usd": str(snap.last_trade_price_usd),
                "pool_age_seconds": snap.pool_age_seconds,
            }, trail_path)
            counts["resnapped"] += 1
            seen.add(t_offset_hour_key)
            # Be polite to DexScreener
            await asyncio.sleep(0.3)
    finally:
        if own_dex:
            await dex.close()
    return counts


async def resnap_loop(interval_minutes: float = RESNAP_INTERVAL_MINUTES) -> None:
    log.info("a2_resnap_loop_starting", interval_minutes=interval_minutes)
    while True:
        try:
            counts = await resnap_once()
            log.info("a2_resnap_tick", **counts)
        except Exception as e:  # noqa: BLE001
            log.warning("a2_resnap_failed", error=str(e))
        await asyncio.sleep(interval_minutes * 60.0)
