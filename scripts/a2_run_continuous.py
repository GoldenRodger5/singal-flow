"""A2 continuous runner — collects shadow-mode data across multiple days.

What it does:
  * Every `--shadow-interval-min` minutes: pull DexScreener trending Solana tokens,
    enrich each one (DexScreener + Helius + Birdeye), apply RugFilter, append
    one observation per token to logs/a2_shadow.jsonl.
  * Every `--harvest-interval-hours` hours: walk the shadow log, find any
    observation whose 24h window has matured, fetch OHLCV via Birdeye, write
    outcome record. Idempotent — already-harvested obs_ids skipped.
  * Every `--summary-interval-hours` hours: print a fresh outcomes summary.

Safe to leave running for days. Robust to transient API failures (one bad
iteration is logged and the loop continues). Clean shutdown on SIGINT/SIGTERM.

Usage:
  # Default cadence (30min shadow, 6h harvest, 24h summary), runs forever:
  python -m scripts.a2_run_continuous

  # Run for one iteration to smoke-test:
  python -m scripts.a2_run_continuous --max-iterations 1

  # Faster cadence for early data collection:
  python -m scripts.a2_run_continuous --shadow-interval-min 15

Deployment options:
  # in a tmux/screen session — simplest:
  tmux new -s a2 'python -m scripts.a2_run_continuous'

  # background with nohup, logs to file:
  nohup python -m scripts.a2_run_continuous > logs/a2_continuous.out 2>&1 &

  # macOS launchd: see docs/A2_KEYS_AND_NEXT.md for a sample plist.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

from helios.ops import configure_logging, get_logger
from helios.ops.backup import backup_to_github
from helios.strategies.a2_meme_snipe import RugFilter
from helios.strategies.a2_meme_snipe.enricher import SnapshotEnricher
from helios.strategies.a2_meme_snipe.harvester import harvest
from helios.strategies.a2_meme_snipe.log import (
    read_observations,
    read_outcomes,
    write_observation,
)

load_dotenv()
log = get_logger("a2_continuous")

STATUS_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a2_status.json"

# Global stop flag — set by signal handler; checked by loop & interruptible sleep
_STOP = False


def _write_status(state: dict) -> None:
    """Atomic-ish write of a status snapshot — readable any time with `cat logs/a2_status.json`."""
    parent = STATUS_PATH.parent
    target = parent.resolve() if parent.is_symlink() else parent
    try:
        target.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    tmp = STATUS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    tmp.replace(STATUS_PATH)


def _install_signal_handlers() -> None:
    def _handle(signum, frame):  # noqa: ANN001 ARG001
        global _STOP
        _STOP = True
        print(f"\n[continuous] signal {signum} received — finishing current step then exiting", flush=True)
    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)


async def _interruptible_sleep(seconds: float) -> None:
    """Sleep in small chunks so a SIGINT acts within ~2 seconds."""
    end = time.time() + seconds
    while time.time() < end and not _STOP:
        await asyncio.sleep(min(2.0, max(0.0, end - time.time())))


async def fetch_trending_solana(limit: int = 20) -> list[str]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get("https://api.dexscreener.com/token-profiles/latest/v1")
        resp.raise_for_status()
        return [
            p["tokenAddress"]
            for p in resp.json()
            if p.get("chainId") == "solana" and p.get("tokenAddress")
        ][:limit]


async def run_one_shadow(
    enricher: SnapshotEnricher,
    rug: RugFilter,
    limit: int,
    relax_p02: bool,
) -> tuple[int, int, int]:
    """One shadow batch. Returns (n_pass, n_reject, n_enrich_failed)."""
    try:
        mints = await fetch_trending_solana(limit)
    except Exception as e:  # noqa: BLE001
        log.warning("trending_fetch_failed", error=str(e))
        return (0, 0, 0)

    n_pass, n_reject, n_fail = 0, 0, 0
    for i, mint in enumerate(mints):
        if _STOP:
            break
        if i > 0:
            await _interruptible_sleep(1.2)
        try:
            snap = await enricher.enrich(mint)
        except Exception as e:  # noqa: BLE001
            log.warning("enrich_failed", mint=mint, error=str(e))
            n_fail += 1
            continue
        if snap is None:
            continue
        if relax_p02 and not snap.dev_history_known:
            snap = replace(snap, dev_history_known=True, dev_rug_history_count=0)
        report = rug.check(snap)
        write_observation(snap, report.decision.value, list(report.reasons))
        if report.passed:
            n_pass += 1
        else:
            n_reject += 1
    return n_pass, n_reject, n_fail


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow-interval-min", type=float, default=30.0,
                        help="Minutes between shadow detection batches (default 30)")
    parser.add_argument("--harvest-interval-hours", type=float, default=6.0,
                        help="Hours between outcome harvests (default 6)")
    parser.add_argument("--summary-interval-hours", type=float, default=24.0,
                        help="Hours between summary printouts (default 24)")
    parser.add_argument("--shadow-limit", type=int, default=20,
                        help="Max tokens per shadow batch (default 20)")
    parser.add_argument("--max-iterations", type=int, default=None,
                        help="Stop after N shadow iterations (default: unlimited)")
    parser.add_argument("--no-relax-p02", action="store_true",
                        help="Enforce P02 (dev_history_unknown) strictly. Default: relax for data collection.")
    parser.add_argument("--backup-interval-hours", type=float, default=6.0,
                        help="Hours between GitHub backup pushes (default 6; needs GITHUB_TOKEN + GITHUB_REPO env vars)")
    args = parser.parse_args()

    configure_logging(level="WARNING")  # noisy adapter logs go to JSON sink; stdout stays clean
    _install_signal_handlers()

    print(f"[continuous] starting | shadow={args.shadow_interval_min}m  "
          f"harvest={args.harvest_interval_hours}h  summary={args.summary_interval_hours}h  "
          f"limit={args.shadow_limit}  relax_p02={not args.no_relax_p02}", flush=True)

    enricher = SnapshotEnricher()
    rug = RugFilter()

    iteration = 0
    last_harvest = 0.0
    last_summary = 0.0
    last_backup = 0.0
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def update_status(stage: str, **extra) -> None:
        try:
            total_obs = len(list(read_observations()))
            total_out = len(list(read_outcomes()))
            _write_status({
                "started_at_utc": started_at,
                "last_update_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "iteration": iteration,
                "stage": stage,
                "total_observations_logged": total_obs,
                "total_outcomes_harvested": total_out,
                "shadow_interval_min": args.shadow_interval_min,
                "harvest_interval_hours": args.harvest_interval_hours,
                **extra,
            })
        except Exception:  # noqa: BLE001
            pass

    update_status("starting")
    try:
        while not _STOP:
            iteration += 1
            iter_start = time.time()
            iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

            try:
                n_pass, n_reject, n_fail = await run_one_shadow(
                    enricher, rug,
                    args.shadow_limit,
                    relax_p02=not args.no_relax_p02,
                )
                total_obs = len(list(read_observations()))
                dt = time.time() - iter_start
                print(f"[{iso}] iter={iteration:>4d}  shadow ok  "
                      f"pass={n_pass:>2d} reject={n_reject:>2d} fail={n_fail:>2d}  "
                      f"total_logged={total_obs:>5d}  ({dt:.1f}s)", flush=True)
                update_status("idle", last_iter_pass=n_pass, last_iter_reject=n_reject, last_iter_fail=n_fail)
            except Exception as e:  # noqa: BLE001
                log.exception("shadow_iter_failed", error=str(e))
                print(f"[{iso}] iter={iteration} SHADOW FAILED: {e}", flush=True)

            now = time.time()
            if now - last_harvest > args.harvest_interval_hours * 3600:
                try:
                    update_status("harvesting")
                    print(f"[{iso}] running harvest...", flush=True)
                    counts = await harvest()
                    total_out = len(list(read_outcomes()))
                    print(f"[{iso}] harvest ok  processed={counts['processed']:>4d}  "
                          f"skipped_recent={counts['skipped_recent']:>4d}  "
                          f"skipped_done={counts['skipped_done']:>4d}  "
                          f"failed={counts['failed']:>4d}  total_outcomes={total_out}", flush=True)
                except Exception as e:  # noqa: BLE001
                    log.exception("harvest_failed", error=str(e))
                    print(f"[{iso}] HARVEST FAILED: {e}", flush=True)
                last_harvest = now

            # Periodic GitHub backup of JSONL files (fire-and-forget).
            # Skipped silently if GITHUB_TOKEN/GITHUB_REPO env vars aren't set.
            if now - last_backup > args.backup_interval_hours * 3600:
                async def _do_backup(t=iso):
                    try:
                        ok = await backup_to_github()
                        print(f"[{t}] backup -> github  {'ok' if ok else 'skipped/failed'}", flush=True)
                    except Exception as e:  # noqa: BLE001
                        log.exception("backup_failed", error=str(e))
                asyncio.create_task(_do_backup())
                last_backup = now

            if now - last_summary > args.summary_interval_hours * 3600:
                try:
                    outcomes = list(read_outcomes())
                    if outcomes:
                        # Lazy import to avoid circular reference at module load
                        from scripts.a2_outcomes import print_summary
                        print_summary(outcomes, window="24h", slippage_pct=0.10)
                except Exception as e:  # noqa: BLE001
                    log.exception("summary_failed", error=str(e))
                last_summary = now

            if args.max_iterations and iteration >= args.max_iterations:
                print(f"[continuous] hit --max-iterations={args.max_iterations}", flush=True)
                break
            if _STOP:
                break

            # Sleep until next shadow tick, accounting for iteration duration
            sleep_seconds = max(1.0, args.shadow_interval_min * 60.0 - (time.time() - iter_start))
            await _interruptible_sleep(sleep_seconds)
    finally:
        try:
            await enricher.close()
        except Exception:  # noqa: BLE001
            pass
        print(f"\n[continuous] shut down cleanly after {iteration} iteration(s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
