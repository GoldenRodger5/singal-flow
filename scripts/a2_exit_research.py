"""Run the exit-policy grid against real candle paths for harvested A2 tokens.

Re-fetches 1m OHLCV from Birdeye for each token in a2_outcomes.jsonl, runs the
full exit-policy grid, prints the ranked results + the decisive verdict.

Run inside the Railway container (has the volume + Birdeye key):
    railway ssh "cd /app && python -m scripts.a2_exit_research"
Or locally with .env:
    python -m scripts.a2_exit_research --limit 100
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from helios.data.adapters.birdeye import BirdeyeAdapter
from helios.ops import configure_logging, get_logger
from helios.strategies.a2_meme_snipe.exit_research import (
    evaluate_policies,
    load_outcome_tokens,
)
from helios.strategies.a2_meme_snipe.outcomes import Candle, parse_birdeye_candles

load_dotenv()

OUTCOMES_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a2_outcomes.jsonl"
WINDOW_HOURS = 4


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Cap tokens for a fast run")
    parser.add_argument("--slippage", type=float, default=0.10, help="per-leg slippage fraction")
    parser.add_argument("--window-hours", type=int, default=WINDOW_HOURS)
    args = parser.parse_args()

    configure_logging(level="WARNING")
    log = get_logger("a2_exit_research")

    tokens = load_outcome_tokens(OUTCOMES_PATH)
    if args.limit:
        tokens = tokens[: args.limit]
    print(f"Loaded {len(tokens)} tokens from {OUTCOMES_PATH}")
    if not tokens:
        print("No tokens — nothing to research.")
        return 1

    birdeye = BirdeyeAdapter()
    token_candles: list[tuple[float, list[Candle]]] = []
    fetched, failed = 0, 0
    try:
        for i, (mint, entry_unix, entry_price) in enumerate(tokens):
            try:
                raw = await birdeye.fetch_ohlcv(
                    mint, entry_unix, entry_unix + args.window_hours * 3600, interval="1m"
                )
            except Exception as e:  # noqa: BLE001
                failed += 1
                continue
            candles = parse_birdeye_candles(raw)
            # Only keep candles at/after entry
            candles = [c for c in candles if c.unix_time >= entry_unix]
            if candles:
                token_candles.append((entry_price, candles))
                fetched += 1
            if (i + 1) % 25 == 0:
                print(f"  ...fetched {fetched}/{i+1} (failed {failed})", flush=True)
    finally:
        await birdeye.close()

    print(f"\nUsable token paths: {len(token_candles)}  (failed fetches: {failed})\n")
    if not token_candles:
        print("No usable candle data — Birdeye may have purged history for dead tokens.")
        return 1

    results = evaluate_policies(token_candles, slippage_each_leg=args.slippage)

    print("=" * 92)
    print(f"{'EXIT-POLICY GRID — net of ' + str(int(args.slippage*100)) + '% slippage/leg, ' + str(len(token_candles)) + ' tokens':^92}")
    print("=" * 92)
    print(f"{'policy':<26}{'n':>5}{'mean_net':>11}{'med_net':>10}{'win%':>8}{'p90_net':>11}{'mean_raw':>11}")
    print("-" * 92)
    for r in results[:25]:
        print(f"{r.name:<26}{r.n:>5}{r.mean_net:>+10.1%}{r.median_net:>+9.1%}"
              f"{r.win_rate:>7.1%}{r.p90_net:>+10.1%}{r.mean_raw:>+10.1%}")

    print("\n" + "=" * 92)
    best = results[0]
    positive = [r for r in results if r.mean_net > 0]
    print("VERDICT:")
    if best.mean_net > 0:
        print(f"  Best policy '{best.name}': mean net {best.mean_net:+.1%} per shot after slippage.")
        print(f"  {len(positive)} of {len(results)} policies are positive-EV.")
        print(f"  => Memecoin sniping is POTENTIALLY viable with this exit engine.")
        print(f"     Next: validate out-of-sample + check the win-rate/variance is survivable.")
    else:
        print(f"  Best policy '{best.name}' still only {best.mean_net:+.1%} net per shot.")
        print(f"  ZERO of {len(results)} policies clear positive-EV after {int(args.slippage*100)}% slippage.")
        print(f"  => On THIS universe (DexScreener trending), no exit rule rescues it.")
        print(f"     The slippage + dump dynamics dominate. Memecoin-trending sniping is dead for us.")
        print(f"     Implication: edge (if any) requires earlier detection (first 120s post-launch)")
        print(f"     where slippage is lower and the pump hasn't happened yet — needs paid Helius WS.")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
