"""A3 — Liquidation cascade hunter on perpetual futures.

Thesis:
  When open-interest + leverage clusters near a price level, that level becomes
  a magnet for price action. As price approaches a heavy liquidation pocket,
  forced selling/buying accelerates the move, exhausts the local liquidity, and
  reverses sharply once the cascade clears.

  Two trade variants:
    Variant A — FADE the cascade exhaustion: enter against the cascade direction
                AFTER the bulk of liquidations has cleared. Edge: mean reversion
                from over-extended positions. Higher hit-rate, smaller magnitudes.
    Variant B — RIDE the cascade: enter in the cascade direction once the
                liquidation wall starts breaking. Edge: momentum continuation
                through clusters. Lower hit-rate, bigger magnitudes.

For v1 we run BOTH variants in shadow mode and let the outcome data tell us
which works (or if either does) on this universe + this regime.

Universe: BTC + ETH + SOL perpetuals on Kraken Futures (CFTC-compliant for US).
Data sources:
  - Kraken Futures funding-rate + OHLC (already-integrated adapter)
  - Coinglass aggregator for OI + liquidation history (public free tier)

Honest about the constraint:
  Kraken Futures alone gives us a fraction of crypto perp OI; the bulk lives on
  Binance + Hyperliquid + Bybit which we cannot legally trade as US residents.
  However the OI on Kraken IS reflective of global flow — when global perps see
  cascade conditions, Kraken's price tracks. The trade venue is Kraken; the
  signal venue is global OI from Coinglass.
"""
from helios.strategies.a3_liq_hunt.detector import (
    LiquidationCluster,
    LiquidationDetector,
    LiquidationEvent,
)

__all__ = ["LiquidationCluster", "LiquidationDetector", "LiquidationEvent"]
