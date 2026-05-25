"""Outcome metrics — pure functions over an OHLCV series + an entry timestamp.

Given a list of OHLCV candles and an entry time T, compute what would have
happened for various exit policies. This is the ground truth that calibrates
the filter.

Key metrics:
    max_pump_pct       max(high) since T, vs entry price
    max_dump_pct       1 - min(low) since T, vs entry price
    final_pct          last(close) at end of window, vs entry price
    time_to_2x_sec     seconds from T until first bar whose high >= 2 * entry
    time_to_peak_sec   seconds from T until the bar with max high

Honest slippage: the metrics use raw prices. The runner overlays a slippage
budget per leg (default 10% in / 10% out for memecoins) when computing the
"realized would-have-pnl" report.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Candle:
    unix_time: int
    o: float
    h: float
    l: float
    c: float
    v: float


@dataclass(frozen=True, slots=True)
class Outcome:
    entry_price: float
    entry_unix: int
    window_unix: int                    # last unix time in the window we evaluated
    n_candles: int
    final_pct: float                    # close-to-close, raw
    max_pump_pct: float                 # max high vs entry
    max_dump_pct: float                 # max drawdown from entry, as fraction (positive number)
    hit_2x: bool
    hit_5x: bool
    hit_10x: bool
    time_to_2x_sec: int | None
    time_to_peak_sec: int


def parse_birdeye_candles(items: list[dict]) -> list[Candle]:
    out: list[Candle] = []
    for it in items:
        out.append(Candle(
            unix_time=int(it["unixTime"]),
            o=float(it["o"]),
            h=float(it["h"]),
            l=float(it["l"]),
            c=float(it["c"]),
            v=float(it.get("v", 0.0)),
        ))
    return out


def compute_outcome(candles: list[Candle], entry_unix: int, entry_price: float) -> Outcome | None:
    """All candles with unix_time >= entry_unix are part of the window."""
    if entry_price <= 0:
        return None
    window = [c for c in candles if c.unix_time >= entry_unix]
    if not window:
        return None

    max_high = max(c.h for c in window)
    min_low = min(c.l for c in window)
    final_close = window[-1].c

    max_pump = (max_high - entry_price) / entry_price
    max_dump = max(0.0, (entry_price - min_low) / entry_price)
    final = (final_close - entry_price) / entry_price

    # First bar to cross 2x threshold
    time_to_2x: int | None = None
    for c in window:
        if c.h >= 2.0 * entry_price:
            time_to_2x = c.unix_time - entry_unix
            break
    # Time to peak
    peak_candle = max(window, key=lambda c: c.h)
    time_to_peak = peak_candle.unix_time - entry_unix

    return Outcome(
        entry_price=entry_price,
        entry_unix=entry_unix,
        window_unix=window[-1].unix_time,
        n_candles=len(window),
        final_pct=final,
        max_pump_pct=max_pump,
        max_dump_pct=max_dump,
        hit_2x=max_high >= 2.0 * entry_price,
        hit_5x=max_high >= 5.0 * entry_price,
        hit_10x=max_high >= 10.0 * entry_price,
        time_to_2x_sec=time_to_2x,
        time_to_peak_sec=time_to_peak,
    )


# -------- Exit-policy simulators (operate on the same candle series) --------

def policy_buy_and_hold(outcome: Outcome) -> float:
    """Return = final_pct. Trivial baseline."""
    return outcome.final_pct


def policy_fixed_target_stop(
    candles: list[Candle],
    entry_unix: int,
    entry_price: float,
    target_mult: float = 3.0,
    stop_pct: float = 0.5,
) -> float:
    """First bar to cross target OR stop wins. Stop is fraction of entry (0.5 = -50%)."""
    if entry_price <= 0:
        return 0.0
    target_price = entry_price * target_mult
    stop_price = entry_price * (1.0 - stop_pct)
    for c in candles:
        if c.unix_time < entry_unix:
            continue
        # Conservative: if both target and stop are hit in the same bar, assume stop
        # fired first (we don't have intra-bar order; this is the safe assumption).
        if c.l <= stop_price:
            return -stop_pct
        if c.h >= target_price:
            return target_mult - 1.0
    # Window expired without hitting either — exit at final close
    return (candles[-1].c - entry_price) / entry_price if candles else 0.0


def policy_trailing_stop(
    candles: list[Candle],
    entry_unix: int,
    entry_price: float,
    trail_pct: float = 0.5,
) -> float:
    """Exit when price drops `trail_pct` from running peak. Uses bar lows."""
    if entry_price <= 0:
        return 0.0
    peak = entry_price
    for c in candles:
        if c.unix_time < entry_unix:
            continue
        peak = max(peak, c.h)
        trail_trigger = peak * (1.0 - trail_pct)
        if c.l <= trail_trigger:
            return (trail_trigger - entry_price) / entry_price
    return (candles[-1].c - entry_price) / entry_price if candles else 0.0


def apply_slippage(realized_pct: float, slippage_each_leg_pct: float = 0.10) -> float:
    """Convert a raw price-only return into a realized P&L after slippage on
    both entry and exit legs. Memecoin default: 10% each leg = ~21% round-trip
    drag on a single round-trip ((1-s)/(1+s) - 1 ≈ -2s)."""
    s = slippage_each_leg_pct
    # We bought at (1 + s) * entry_mid_price and sell at (1 - s) * exit_mid_price.
    # raw return r = exit_mid/entry_mid - 1 => realized = (1-s)/(1+s) * (1+r) - 1
    return ((1.0 - s) / (1.0 + s)) * (1.0 + realized_pct) - 1.0
