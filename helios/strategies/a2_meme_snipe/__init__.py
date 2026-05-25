"""A2 — Solana memecoin / new-launch sniping.

Pre-trade filter ("RugFilter") is the edge. Trade size capped per-shot, ruin
budget enforced at the risk overlay, position has hard auto-exit on liquidity
drop or trailing stop.

Build phases:
  A2.1 (this commit): rug filter + token snapshot + DexScreener adapter +
                      strategy skeleton + tests. NO live trading.
  A2.2: live new-pool detection via Helius/Birdeye (needs API key) +
        shadow-mode "would-have-bought" logger.
  A2.3: backtest replay over historical launches; calibrate filter thresholds.
  A2.4: hot-wallet execution via Jupiter aggregator; small live positions.
"""
from helios.strategies.a2_meme_snipe.rug_filter import (
    FilterDecision,
    RugFilter,
    RugFilterConfig,
)
from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot

__all__ = ["FilterDecision", "RugFilter", "RugFilterConfig", "TokenSnapshot"]
