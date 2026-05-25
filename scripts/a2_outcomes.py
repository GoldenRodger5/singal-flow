"""A2 outcome harvest + summary.

  python -m scripts.a2_outcomes              # harvest matured observations + print summary
  python -m scripts.a2_outcomes --summary    # only print summary from existing outcomes
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

from helios.ops import configure_logging
from helios.strategies.a2_meme_snipe.harvester import harvest
from helios.strategies.a2_meme_snipe.log import (
    OUTCOMES_LOG_DEFAULT,
    SHADOW_LOG_DEFAULT,
    read_observations,
    read_outcomes,
)
from helios.strategies.a2_meme_snipe.outcomes import apply_slippage

load_dotenv()


def print_summary(outcomes: list[dict], window: str = "24h", slippage_pct: float = 0.10) -> None:
    if not outcomes:
        print("No outcomes to summarize yet.")
        return

    pass_set, reject_set = [], []
    for r in outcomes:
        win = r.get("windows", {}).get(window)
        if win is None:
            continue
        if r.get("filter_decision") == "PASS":
            pass_set.append(win)
        else:
            reject_set.append(win)

    def stats(label: str, group: list[dict]) -> None:
        if not group:
            print(f"\n  {label}: n=0")
            return
        finals = [w["core"]["final_pct"] for w in group]
        peaks = [w["core"]["max_pump_pct"] for w in group]
        dumps = [w["core"]["max_dump_pct"] for w in group]
        hit2 = sum(1 for w in group if w["core"]["hit_2x"])
        hit5 = sum(1 for w in group if w["core"]["hit_5x"])
        hit10 = sum(1 for w in group if w["core"]["hit_10x"])
        # Policy returns after slippage
        bnh = [apply_slippage(w["policies"]["buy_and_hold"], slippage_pct) for w in group]
        target = [apply_slippage(w["policies"]["target3x_stop50"], slippage_pct) for w in group]
        trail = [apply_slippage(w["policies"]["trailing50"], slippage_pct) for w in group]
        n = len(group)
        print(f"\n  {label}: n={n}")
        print(f"    raw final return  median={statistics.median(finals):.2%}  mean={statistics.mean(finals):.2%}")
        print(f"    max pump          median={statistics.median(peaks):.2%}  max={max(peaks):.2%}")
        print(f"    max dump          median={statistics.median(dumps):.2%}  max={max(dumps):.2%}")
        print(f"    hit ≥2x: {hit2}/{n} ({hit2/n:.1%})   "
              f"≥5x: {hit5}/{n} ({hit5/n:.1%})   "
              f"≥10x: {hit10}/{n} ({hit10/n:.1%})")
        print(f"    realized (slippage {slippage_pct:.0%}/leg):")
        print(f"      buy-and-hold        mean={statistics.mean(bnh):+.2%}  median={statistics.median(bnh):+.2%}")
        print(f"      target3x/stop-50%   mean={statistics.mean(target):+.2%}  median={statistics.median(target):+.2%}")
        print(f"      trailing-50%        mean={statistics.mean(trail):+.2%}  median={statistics.median(trail):+.2%}")

    print(f"\n==== A2 OUTCOME SUMMARY ({window} window, {slippage_pct:.0%} slippage/leg) ====")
    stats("FILTER PASS", pass_set)
    stats("FILTER REJECT", reject_set)

    # Reject-by-code analysis: which rejection codes would have caught winners?
    by_code: dict[str, list[dict]] = defaultdict(list)
    for r in outcomes:
        if r.get("filter_decision") != "REJECT":
            continue
        win = r.get("windows", {}).get(window)
        if win is None:
            continue
        for code in r.get("filter_reasons", []):
            short = code.split("_")[0]
            by_code[short].append(win)
    if by_code:
        print(f"\n  REJECTION-CODE ANALYSIS (would these rejections have missed winners?):")
        print(f"  {'code':<6} {'n':>4} {'hit≥2x':>7} {'med raw':>9} {'med trail50 net':>16}")
        for code, group in sorted(by_code.items()):
            n = len(group)
            h2 = sum(1 for w in group if w["core"]["hit_2x"])
            med_raw = statistics.median([w["core"]["final_pct"] for w in group])
            med_trail = statistics.median([
                apply_slippage(w["policies"]["trailing50"], slippage_pct) for w in group
            ])
            print(f"  {code:<6} {n:>4} {h2/n:>6.1%} {med_raw:>9.1%} {med_trail:>15.1%}")
        print("  (high hit-rate in a reject bucket => that filter check may be too strict)")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="Skip harvest; print summary only")
    parser.add_argument("--window", default="24h", choices=["1h", "4h", "24h"])
    parser.add_argument("--slippage", type=float, default=0.10, help="per-leg slippage fraction")
    args = parser.parse_args()

    configure_logging(level="WARNING")

    if not args.summary:
        print(f"Harvesting outcomes from {SHADOW_LOG_DEFAULT}...")
        if not Path(SHADOW_LOG_DEFAULT).exists():
            print(f"  No shadow log yet at {SHADOW_LOG_DEFAULT}. Run a2_shadow_mode --log first.")
            return 0
        counts = await harvest()
        print(f"  processed={counts['processed']}  skipped_recent={counts['skipped_recent']}  "
              f"skipped_done={counts['skipped_done']}  failed={counts['failed']}")

    obs_n = len(list(read_observations()))
    outcomes = list(read_outcomes())
    print(f"\nObservations logged: {obs_n}    Outcomes harvested: {len(outcomes)}")
    print_summary(outcomes, window=args.window, slippage_pct=args.slippage)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
