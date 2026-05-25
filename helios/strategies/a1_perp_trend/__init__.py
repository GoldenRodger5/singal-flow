"""A1 — Crypto perp trend / breakout, leveraged 3-5x.

Universe (Kraken Futures, CFTC-regulated): BTC-PERP, ETH-PERP, SOL-PERP at v1.
Holding period: hours to days.
Sizing: fractional Kelly off conformal lower bound (helios.sizing.kelly).
Risk: per-strategy 5x leverage cap; halved by drawdown brake.

Entry thesis (gradient-boosted classifier):
  * Recent realized vol expanding (Z-score on 20-bar std)
  * Funding rate aligned with proposed direction
  * Open-interest trend confirming
  * Momentum (multi-horizon return Z-scores)
  * Volume surge confirmation

Exit:
  * Hard invalidation at structural level (recent swing low/high) — set in Signal
  * Trailing stop after 2R achieved
  * Scale-outs at 3R / 5R / 10R (handled by execution layer)
"""
from helios.strategies.a1_perp_trend.strategy import A1PerpTrend

__all__ = ["A1PerpTrend"]
