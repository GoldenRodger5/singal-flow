"""Slippage model. Pure function.

Models the cost of execution as a function of:
  - participation:   order_size / average_volume_in_lookback_window
  - volatility:      recent realized vol (one bar's std-of-returns)
  - spread:          bid-ask spread in bps

Calibration: a small linear model in participation^0.5 + a spread floor.
Coefficients chosen to match published empirical curves for crypto majors;
they will be re-fit against live fill data once we have it (target: paper
realized slippage within 20% of model).

Slippage matters more than retail thinks. A strategy with 50 bps backtest
edge and a 30 bps slippage model breaks even live. Garbage in, garbage out.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SlippageInputs:
    order_size: float           # in base units (BTC, shares, ...)
    adv: float                  # average bar volume over a recent window
    volatility_pct: float       # bar volatility, e.g. 0.005 = 50 bps stdev
    spread_bps: float           # current bid-ask spread in bps

    def __post_init__(self) -> None:
        if self.order_size < 0 or self.adv < 0 or self.volatility_pct < 0 or self.spread_bps < 0:
            raise ValueError("All slippage inputs must be non-negative")


def estimate_slippage_bps(inp: SlippageInputs) -> float:
    """Return expected slippage in bps for a market order.

    Components:
      - Half-spread cost (cross the book): spread_bps / 2
      - Impact: k * sqrt(participation) * vol  (Almgren-style square-root law)
      - Floor: never less than half-spread

    Coefficients are conservative defaults; replace via calibration in Phase 2.
    """
    if inp.adv <= 0:
        # If we don't know ADV, assume full one-bar participation — worst case
        participation = 1.0
    else:
        participation = min(1.0, inp.order_size / inp.adv)

    half_spread = inp.spread_bps / 2.0
    # Impact in bps: 10000 * k * sqrt(participation) * vol
    k = 0.5  # impact coefficient; will be calibrated
    impact_bps = 10000.0 * k * (participation ** 0.5) * inp.volatility_pct
    return max(half_spread, half_spread + impact_bps)
