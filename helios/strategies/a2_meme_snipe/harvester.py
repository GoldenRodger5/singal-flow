"""Outcome harvester — reads shadow log, fetches OHLCV for each observation
whose outcome window has matured, computes outcomes, writes to outcomes log.

Idempotent: previously-harvested obs_ids are skipped.

For each observation with timestamp T, we compute outcomes at three windows:
    1h   close at T+1h vs entry, plus max/min in the window
    4h   close at T+4h vs entry, plus max/min in the window
    24h  close at T+24h vs entry, plus max/min in the window

Entry price is snapshot.last_trade_price_usd at observation time. OHLCV is
1-minute candles from Birdeye starting at T - 60s (one bar back for the entry
reference) through T + window_seconds + 60s (one bar past for safety).
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from helios.data.adapters.geckoterminal import GeckoTerminalAdapter
from helios.ops import get_logger
from helios.strategies.a2_meme_snipe.log import (
    OUTCOMES_LOG_DEFAULT,
    SHADOW_LOG_DEFAULT,
    harvested_obs_ids,
    read_observations,
    write_outcome,
)
from helios.strategies.a2_meme_snipe.outcomes import (
    compute_outcome,
    parse_birdeye_candles,
    policy_buy_and_hold,
    policy_fixed_target_stop,
    policy_trailing_stop,
)

log = get_logger(__name__)

WINDOWS = {"1h": 3600, "4h": 14400, "24h": 86400}


async def harvest(
    shadow_path: Path = SHADOW_LOG_DEFAULT,
    outcomes_path: Path = OUTCOMES_LOG_DEFAULT,
    birdeye: GeckoTerminalAdapter | None = None,
    request_sleep_seconds: float = 1.1,
) -> dict[str, int]:
    """Walk observations; for each one whose largest window is matured, fetch
    OHLCV and write an outcome record. Returns counts of processed/skipped."""
    own = birdeye is None
    birdeye = birdeye or GeckoTerminalAdapter()
    counts = {"processed": 0, "skipped_recent": 0, "skipped_done": 0, "failed": 0}
    seen = harvested_obs_ids(outcomes_path)
    now = datetime.now(timezone.utc).timestamp()
    obs_list = list(read_observations(shadow_path))
    try:
        for obs in obs_list:
            obs_id = obs.get("obs_id")
            if not obs_id or obs_id in seen:
                counts["skipped_done"] += 1
                continue
            try:
                ts_iso = obs["timestamp_iso"]
                ts = datetime.fromisoformat(ts_iso).timestamp()
            except (KeyError, ValueError):
                counts["failed"] += 1
                continue
            # Use the largest window we know about — if it isn't matured, skip
            largest = max(WINDOWS.values())
            if now - ts < largest:
                counts["skipped_recent"] += 1
                continue

            entry_price_raw = obs.get("snapshot", {}).get("last_trade_price_usd")
            try:
                entry_price = float(Decimal(str(entry_price_raw)))
            except (TypeError, ValueError):
                counts["failed"] += 1
                continue
            if entry_price <= 0:
                counts["failed"] += 1
                continue

            mint = obs.get("mint")
            if not mint:
                counts["failed"] += 1
                continue

            time_from = int(ts) - 60
            time_to = int(ts) + largest + 60
            try:
                raw_candles = await birdeye.fetch_ohlcv(mint, time_from, time_to, interval="1m")
                await asyncio.sleep(request_sleep_seconds)
            except Exception as e:  # noqa: BLE001
                log.warning("ohlcv_fetch_failed", mint=mint, obs_id=obs_id, error=str(e))
                counts["failed"] += 1
                continue

            candles = parse_birdeye_candles(raw_candles)
            if not candles:
                counts["failed"] += 1
                continue

            entry_unix = int(ts)
            outcomes_per_window: dict[str, dict] = {}
            for label, secs in WINDOWS.items():
                window_candles = [c for c in candles if c.unix_time <= entry_unix + secs]
                o = compute_outcome(window_candles, entry_unix, entry_price)
                if o is None:
                    continue
                outcomes_per_window[label] = {
                    "core": asdict(o),
                    "policies": {
                        "buy_and_hold": policy_buy_and_hold(o),
                        "target3x_stop50": policy_fixed_target_stop(
                            window_candles, entry_unix, entry_price, 3.0, 0.5
                        ),
                        "trailing50": policy_trailing_stop(
                            window_candles, entry_unix, entry_price, 0.5
                        ),
                    },
                }
            if not outcomes_per_window:
                counts["failed"] += 1
                continue

            record = {
                "obs_id": obs_id,
                "mint": mint,
                "entry_unix": entry_unix,
                "entry_price_usd": entry_price,
                "filter_decision": obs.get("filter_decision"),
                "filter_reasons": obs.get("filter_reasons", []),
                "windows": outcomes_per_window,
                "harvested_iso": datetime.now(timezone.utc).isoformat(),
            }
            write_outcome(record, outcomes_path)
            counts["processed"] += 1
    finally:
        if own:
            await birdeye.close()

    return counts
