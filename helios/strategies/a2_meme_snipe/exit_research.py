"""Exit-policy research — find the best exit rule for memecoin entries.

The A2 outcome data showed: tokens pump (+30% median max) then dump (-43%
median final). The filter is sound; the problem is exit timing. This module
answers the decisive question:

    Is there ANY exit policy that makes buying these tokens positive-EV
    after realistic slippage?

If yes → A2 becomes viable with a better exit engine + faster detection.
If no  → memecoin sniping on this universe is structurally dead for us, and
         we stop pouring effort into A2 regardless of detection speed.

Method:
  1. Read a2_outcomes.jsonl → list of (mint, entry_unix, entry_price).
  2. Re-fetch 1-minute OHLCV from Birdeye for [entry, entry+window].
  3. Run a grid of exit policies over each token's real candle path.
  4. Average net-of-slippage return across all tokens per policy.
  5. Rank policies; report whether any clears zero after slippage.

Policies tested:
  - fixed_target_stop(T, S)     take profit at T×, hard stop at -S%
  - trailing(P)                  exit P% below running peak
  - time_exit(M)                 sell at +M minutes regardless
  - target_or_time(T, M)         take profit at T× OR sell at +M min
  - momentum_exit(W, D)          sell when price drops D% over last W minutes
                                 (captures "sell into the dump after the pump")
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Callable, Optional

from helios.strategies.a2_meme_snipe.outcomes import Candle, apply_slippage


# ---------- Exit policy simulators (operate on real candle paths) ----------

def sim_fixed_target_stop(candles: list[Candle], entry: float, target_mult: float, stop_pct: float) -> float:
    if entry <= 0:
        return 0.0
    tp = entry * target_mult
    sl = entry * (1.0 - stop_pct)
    for c in candles:
        if c.l <= sl:        # conservative: stop fires first if both hit same bar
            return -stop_pct
        if c.h >= tp:
            return target_mult - 1.0
    return (candles[-1].c - entry) / entry if candles else 0.0


def sim_trailing(candles: list[Candle], entry: float, trail_pct: float) -> float:
    if entry <= 0:
        return 0.0
    peak = entry
    for c in candles:
        peak = max(peak, c.h)
        trigger = peak * (1.0 - trail_pct)
        if c.l <= trigger:
            return (trigger - entry) / entry
    return (candles[-1].c - entry) / entry if candles else 0.0


def sim_time_exit(candles: list[Candle], entry: float, minutes: int) -> float:
    if entry <= 0 or not candles:
        return 0.0
    idx = min(minutes, len(candles)) - 1
    return (candles[idx].c - entry) / entry


def sim_target_or_time(candles: list[Candle], entry: float, target_mult: float, minutes: int) -> float:
    if entry <= 0:
        return 0.0
    tp = entry * target_mult
    for i, c in enumerate(candles):
        if c.h >= tp:
            return target_mult - 1.0
        if i + 1 >= minutes:
            return (c.c - entry) / entry
    return (candles[-1].c - entry) / entry if candles else 0.0


def sim_momentum_exit(candles: list[Candle], entry: float, window_min: int, drop_pct: float,
                      min_gain_to_arm: float = 0.0) -> float:
    """Ride until momentum turns: once price has gained >= min_gain_to_arm, exit
    the moment it drops `drop_pct` over the trailing `window_min` minutes.
    Captures 'sell into the dump after the pump.'"""
    if entry <= 0 or not candles:
        return 0.0
    armed = min_gain_to_arm <= 0.0
    for i, c in enumerate(candles):
        gain = (c.h - entry) / entry
        if not armed and gain >= min_gain_to_arm:
            armed = True
        if armed and i >= window_min:
            past = candles[i - window_min].c
            if past > 0 and (c.c - past) / past <= -drop_pct:
                return (c.c - entry) / entry
    return (candles[-1].c - entry) / entry if candles else 0.0


@dataclass(frozen=True, slots=True)
class PolicySpec:
    name: str
    fn: Callable[[list[Candle], float], float]


def build_policy_grid() -> list[PolicySpec]:
    specs: list[PolicySpec] = []
    # Fixed target + stop
    for t in (1.25, 1.5, 2.0, 3.0, 5.0):
        for s in (0.3, 0.5, 0.7):
            specs.append(PolicySpec(
                f"target{t}x_stop{int(s*100)}",
                lambda c, e, t=t, s=s: sim_fixed_target_stop(c, e, t, s),
            ))
    # Trailing
    for p in (0.2, 0.3, 0.5):
        specs.append(PolicySpec(f"trail{int(p*100)}", lambda c, e, p=p: sim_trailing(c, e, p)))
    # Time exits
    for m in (5, 15, 30, 60, 120):
        specs.append(PolicySpec(f"time{m}m", lambda c, e, m=m: sim_time_exit(c, e, m)))
    # Target or time
    for t in (1.5, 2.0, 3.0):
        for m in (15, 30, 60):
            specs.append(PolicySpec(
                f"target{t}x_or_{m}m",
                lambda c, e, t=t, m=m: sim_target_or_time(c, e, t, m),
            ))
    # Momentum exit (sell into the dump)
    for w in (3, 5, 10):
        for d in (0.15, 0.25, 0.4):
            for arm in (0.0, 0.3, 1.0):
                specs.append(PolicySpec(
                    f"mom_w{w}_drop{int(d*100)}_arm{int(arm*100)}",
                    lambda c, e, w=w, d=d, arm=arm: sim_momentum_exit(c, e, w, d, arm),
                ))
    return specs


@dataclass
class PolicyResult:
    name: str
    n: int
    mean_raw: float
    median_raw: float
    mean_net: float          # after slippage
    median_net: float
    win_rate: float          # fraction with net > 0
    p90_net: float           # 90th percentile (captures the moonshot tail)


def evaluate_policies(
    token_candles: list[tuple[float, list[Candle]]],
    slippage_each_leg: float = 0.10,
) -> list[PolicyResult]:
    """token_candles: list of (entry_price, candles). Returns ranked PolicyResults."""
    specs = build_policy_grid()
    results: list[PolicyResult] = []
    for spec in specs:
        raws: list[float] = []
        for entry, candles in token_candles:
            if not candles or entry <= 0:
                continue
            raws.append(spec.fn(candles, entry))
        if not raws:
            continue
        nets = [apply_slippage(r, slippage_each_leg) for r in raws]
        nets_sorted = sorted(nets)
        p90 = nets_sorted[int(0.9 * (len(nets_sorted) - 1))] if nets_sorted else 0.0
        results.append(PolicyResult(
            name=spec.name, n=len(raws),
            mean_raw=mean(raws), median_raw=median(raws),
            mean_net=mean(nets), median_net=median(nets),
            win_rate=sum(1 for x in nets if x > 0) / len(nets),
            p90_net=p90,
        ))
    # Rank by mean_net desc (EV is what matters for a many-shots strategy)
    return sorted(results, key=lambda r: -r.mean_net)


def load_outcome_tokens(outcomes_path: Path) -> list[tuple[str, int, float]]:
    """Return (mint, entry_unix, entry_price) for each harvested outcome."""
    out: list[tuple[str, int, float]] = []
    if not outcomes_path.exists():
        return out
    with outcomes_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                mint = rec.get("mint")
                entry_unix = int(rec.get("entry_unix", 0))
                entry_price = float(rec.get("entry_price_usd", 0))
                if mint and entry_unix and entry_price > 0:
                    out.append((mint, entry_unix, entry_price))
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    return out
