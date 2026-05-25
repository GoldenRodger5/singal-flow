"""A8 — Cash-and-carry funding harvest. Delta-neutral perp basis trade.

Mechanism:
  long N units spot + short N units perp  (delta-zero)
  -> earn funding payments on perp short (per-hour relativeFundingRate × notional)
  -> P&L from price moves cancels between legs (basis-noise is the residual)

This is not a prediction. The arithmetic is the strategy.

Entry: trailing-mean annualized funding > entry threshold (e.g. 8% APY)
Exit:  trailing-mean annualized funding < exit threshold  (e.g. 2% APY)
Costs: spot taker + perp taker on both entry and exit
"""
from helios.strategies.a8_cash_carry.backtest import (
    A8Config,
    A8Result,
    backtest_a8,
)

__all__ = ["A8Config", "A8Result", "backtest_a8"]
