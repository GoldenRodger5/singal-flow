"""A2 live runner in PAPER mode against the live Helius websocket.

This is the paper-mode counterpart to the shadow runner: shadow polls
DexScreener trending; this subscribes to actual new-pool events as they
happen on-chain.

Paper mode is the default (SAFETY_LIVE_TRADING env var unset). To go live,
the operator must set:
    SAFETY_LIVE_TRADING=I_UNDERSTAND_THE_RISK
    SOLANA_PRIVATE_KEY=<base58>
on the Railway service. Without both, every swap call is a no-op simulation.

Run locally:
    python -m scripts.a2_live_paper
Or via Railway (separate service from the shadow runner):
    add as a new service in tender-tenderness, set CMD to:
    python -m scripts.a2_live_paper
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv

from helios.ops import configure_logging, get_logger
from helios.strategies.a2_meme_snipe.live_runner import A2LiveRunner, LiveRunnerConfig

load_dotenv()


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-shot-sol", type=float, default=0.05)
    parser.add_argument("--max-concurrent", type=int, default=5)
    parser.add_argument("--max-shots-per-hour", type=int, default=30)
    parser.add_argument("--target-mult", type=float, default=3.0)
    parser.add_argument("--stop-pct", type=float, default=0.50)
    parser.add_argument("--trail-pct", type=float, default=0.50)
    parser.add_argument("--poller", action="store_true",
                        help="Use DexScreener polling instead of Helius WS (fallback)")
    args = parser.parse_args()

    configure_logging(level="INFO")
    log = get_logger("a2_live_paper")

    cfg = LiveRunnerConfig(
        per_shot_sol=args.per_shot_sol,
        max_concurrent_positions=args.max_concurrent,
        max_shots_per_hour=args.max_shots_per_hour,
        target_multiplier=args.target_mult,
        stop_loss_pct=args.stop_pct,
        trailing_stop_pct=args.trail_pct,
    )
    runner = A2LiveRunner(config=cfg)
    log.info("a2_live_paper_starting", config=cfg.__dict__)
    await runner.run(use_websocket=not args.poller)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
