"""Helios unified runner — all 4 strategies in one process.

Runs in parallel:
    A2-shadow  (memecoin filter on DexScreener trending)
    A2-live    (memecoin filter on Helius WS new-pool events, paper-mode)
    A3-shadow  (liquidation cascade detector on BTC/ETH/SOL perps)
    A5-shadow  (sentiment velocity on X + Farcaster)

Each task is supervised — crashes are caught, logged, and restarted with
exponential backoff. One bad task does not bring the others down.

Replaces the per-strategy services with a single Railway service:
    Old: 4 services × $5/mo base = $20/mo before usage
    New: 1 service × $5/mo base = $5/mo before usage
    All log to the same /data/logs volume — easy querying across strategies.

To switch the existing Railway service to this runner:
    Dashboard → tender-tenderness service → Settings → "Custom Start Command":
        python -m scripts.helios_all
    Save. Railway redeploys with all 4 strategies running.

To NOT use it (stay with A2-shadow only):
    Don't change the start command. Current `python -m scripts.a2_run_continuous`
    keeps doing what it always did.

Environment variables (all optional; absent vars degrade gracefully):
    X_API_BEARER         — X (Twitter) bearer for A5; without it A5 runs on Farcaster only
    NEYNAR_API_KEY       — Neynar Farcaster key; without it falls back to public Warpcast
    COINGLASS_API_KEY    — Coinglass premium for A3 heatmap; free tier is fine for shadow
    GITHUB_TOKEN         — periodic backup to data-snapshots branch
    SAFETY_LIVE_TRADING  — must be I_UNDERSTAND_THE_RISK for live trades; default paper
"""
from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys

from dotenv import load_dotenv

from helios.ops import configure_logging
from helios.ops.supervisor import SupervisedTask, run_all

load_dotenv()


def _build_tasks(args) -> list[SupervisedTask]:
    tasks: list[SupervisedTask] = []

    # ---- A2 shadow (DexScreener trending poller, existing behavior) ----
    if not args.disable_a2_shadow:
        async def a2_shadow_factory():
            from scripts.a2_run_continuous import main as a2_main
            # Pass-through CLI args via sys.argv hack — a2_run_continuous parses argparse
            old_argv = sys.argv
            sys.argv = ["scripts.a2_run_continuous"]
            try:
                await a2_main()
            finally:
                sys.argv = old_argv
        tasks.append(SupervisedTask(name="a2_shadow", factory=a2_shadow_factory))

    # ---- A2 live (Helius WS new-pool detector, paper-mode by default) ----
    if args.enable_a2_live:
        from helios.strategies.a2_meme_snipe.live_runner import (
            A2LiveRunner, LiveRunnerConfig,
        )

        async def a2_live_factory():
            runner = A2LiveRunner(config=LiveRunnerConfig(
                per_shot_sol=args.per_shot_sol,
                max_concurrent_positions=args.max_concurrent_positions,
            ))
            await runner.run(use_websocket=not args.poller_only)
        tasks.append(SupervisedTask(name="a2_live", factory=a2_live_factory))

    # ---- A3 shadow (liquidation cascade detection) ----
    if not args.disable_a3:
        from helios.strategies.a3_liq_hunt.runner import A3ShadowRunner

        async def a3_factory():
            await A3ShadowRunner().run()
        tasks.append(SupervisedTask(name="a3_shadow", factory=a3_factory))

    # ---- A5 shadow (sentiment velocity) ----
    if not args.disable_a5:
        from helios.strategies.a5_sentiment.runner import A5ShadowRunner

        async def a5_factory():
            await A5ShadowRunner().run()
        tasks.append(SupervisedTask(name="a5_shadow", factory=a5_factory))

    # ---- A3 outcome harvester (measures realized R for past cascade signals) ----
    if not args.disable_a3:
        from helios.strategies.a3_liq_hunt.harvester import harvest_loop as a3_harvest_loop

        async def a3_harvest_factory():
            await a3_harvest_loop(interval_minutes=60.0)
        tasks.append(SupervisedTask(name="a3_harvest", factory=a3_harvest_factory))

    # ---- A5 outcome harvester (resolves ticker→mint, fetches OHLCV, sims P&L) ----
    if not args.disable_a5:
        from helios.strategies.a5_sentiment.harvester import harvest_loop as a5_harvest_loop

        async def a5_harvest_factory():
            await a5_harvest_loop(interval_minutes=60.0)
        tasks.append(SupervisedTask(name="a5_harvest", factory=a5_harvest_factory))

    # ---- A2 token re-snapshot trail (hourly resnap of last-24h tokens) ----
    if not args.disable_a2_shadow:
        from helios.strategies.a2_meme_snipe.resnap_trail import resnap_loop

        async def resnap_factory():
            await resnap_loop(interval_minutes=60.0)
        tasks.append(SupervisedTask(name="a2_resnap", factory=resnap_factory))

    return tasks


def _install_signal_handlers(loop: asyncio.AbstractEventLoop) -> None:
    """Cancel the gather on SIGINT/SIGTERM for clean shutdown."""
    def _cancel():
        print("\n[helios_all] shutdown signal — cancelling all tasks", flush=True)
        for task in asyncio.all_tasks(loop):
            task.cancel()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _cancel)
        except NotImplementedError:
            # Not all platforms support add_signal_handler (Windows)
            signal.signal(sig, lambda *a: _cancel())


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--disable-a2-shadow", action="store_true")
    # A2-live is OFF by default: Helius Atlas WS is a paid feature (403 on free
    # tier → crash loop), and the DexScreener-poller fallback is redundant with
    # a2_shadow. Opt in with --enable-a2-live only when a paid WS is available.
    parser.add_argument("--enable-a2-live", action="store_true")
    parser.add_argument("--disable-a3", action="store_true")
    parser.add_argument("--disable-a5", action="store_true")
    # A2 live params (paper-mode defaults)
    parser.add_argument("--per-shot-sol", type=float, default=0.05)
    parser.add_argument("--max-concurrent-positions", type=int, default=5)
    parser.add_argument("--poller-only", action="store_true",
                        help="A2 live uses DexScreener polling instead of Helius WS")
    args = parser.parse_args()

    configure_logging(level="INFO")
    print("=" * 70)
    print("Helios unified runner — all enabled strategies in one process")
    print(f"  A2 shadow:  {'OFF' if args.disable_a2_shadow else 'ON'}")
    print(f"  A2 live:    {'ON (paper-mode)' if args.enable_a2_live else 'OFF (paid Helius WS needed)'}")
    print(f"  A3 shadow:  {'OFF' if args.disable_a3 else 'ON'}")
    print(f"  A5 shadow:  {'OFF' if args.disable_a5 else 'ON'}")
    print(f"  Live safety: {'LIVE TRADES ENABLED' if os.getenv('SAFETY_LIVE_TRADING') == 'I_UNDERSTAND_THE_RISK' else 'paper-mode (default)'}")
    print("=" * 70, flush=True)

    loop = asyncio.get_event_loop()
    _install_signal_handlers(loop)

    tasks = _build_tasks(args)
    if not tasks:
        print("[helios_all] all tasks disabled — nothing to run.")
        return 1

    try:
        await run_all(tasks)
    except asyncio.CancelledError:
        print("[helios_all] cancelled cleanly", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
