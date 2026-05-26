"""A8 expanded — multi-symbol cash-and-carry funding harvest with maker-only execution.

Why expand:
  The original A8 backtest (BTC/ETH/SOL only, taker fees) produced ~1% APY net.
  Fees ate 110% of funding income. Two structural fixes:
    1. **More symbols** = more high-funding opportunities. Alt perps regularly
       see 30-80% APY funding bursts; majors rarely.
    2. **Maker-only execution** = ~3x fee reduction (Kraken Futures maker is
       2 bps vs 5 bps taker; Kraken Spot maker is 16 bps vs 26 bps taker).

Maker policy:
  We don't market-order in. We post a resting limit at mid (or mid + tiny edge)
  and wait. If the order doesn't fill within `maker_fill_timeout_seconds`,
  cancel and retry one rung wider. If still no fill after `max_maker_retries`,
  skip the entry. The cost of missing some entries is small; the cost of
  paying taker every time is fatal to the strategy.

Universe (Kraken Futures USD-margined perps):
  Majors: PF_XBTUSD, PF_ETHUSD, PF_SOLUSD
  Liquid alts: PF_AVAXUSD, PF_LINKUSD, PF_DOGEUSD, PF_DOTUSD, PF_ADAUSD,
              PF_MATICUSD, PF_ATOMUSD, PF_NEARUSD, PF_BCHUSD, PF_LTCUSD,
              PF_UNIUSD, PF_AAVEUSD

Backtest happens in-process — we already have the funding-rate history and
perp bars for these symbols via the existing KrakenFuturesMarketData adapter.
This module adds the multi-symbol policy + maker-fee accounting on top.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl

from helios.backtest.tearsheet import TearSheet, tearsheet
from helios.strategies.a8_cash_carry.backtest import A8Config, A8Result, _simulate_symbol

EXPANDED_UNIVERSE = (
    # Majors
    "PF_XBTUSD", "PF_ETHUSD", "PF_SOLUSD",
    # Liquid alts (subset that Kraken Futures actually lists)
    "PF_AVAXUSD", "PF_LINKUSD", "PF_DOGEUSD", "PF_DOTUSD", "PF_ADAUSD",
    "PF_MATICUSD", "PF_ATOMUSD", "PF_NEARUSD", "PF_BCHUSD", "PF_LTCUSD",
    "PF_UNIUSD", "PF_AAVEUSD",
)


@dataclass
class A8ExpandedConfig(A8Config):
    """Expanded-universe config. Inherits A8Config; overrides defaults for
    larger universe + maker fees + slightly higher entry threshold."""
    notional_per_symbol_usd: float = 50.0    # smaller per-symbol; more symbols
    entry_apy: float = 0.10                   # 10% — only the better setups
    exit_apy: float = 0.02
    spot_fee_bps: float = 16.0               # maker on Kraken Spot
    perp_fee_bps: float = 2.0                # maker on Kraken Futures
    maker_fill_timeout_seconds: int = 180    # 3 min — if not filled, skip
    max_maker_retries: int = 2
    universe: tuple[str, ...] = field(default_factory=lambda: EXPANDED_UNIVERSE)
    # Expected maker-fill rate: not every limit order fills. Discount the
    # funding accrual by this factor to model maker selection bias.
    maker_fill_rate: float = 0.7


def backtest_a8_expanded(
    perp_bars_per_symbol: dict[str, pl.DataFrame],
    spot_bars_per_symbol: dict[str, pl.DataFrame],
    funding_per_symbol: dict[str, pl.DataFrame],
    cfg: A8ExpandedConfig | None = None,
) -> A8Result:
    """Run A8 across the expanded universe. Returns aggregate result.

    perp_bars_per_symbol[sym] is a Polars frame: symbol, event_time, close.
    Same shape for spot and funding (funding has funding_rate column).
    """
    cfg = cfg or A8ExpandedConfig()
    per_symbol_stats: dict[str, dict[str, float]] = {}
    all_pnl_by_time: dict[int, float] = {}

    deployed_symbols = []
    for sym in cfg.universe:
        if sym not in perp_bars_per_symbol or sym not in funding_per_symbol:
            continue
        deployed_symbols.append(sym)
        # Use perp as spot proxy when spot history is missing (Kraken Spot only
        # gives ~30 days, perp gives 15+ months)
        spot_df = spot_bars_per_symbol.get(sym, perp_bars_per_symbol[sym])
        # Align as before
        perp_df = perp_bars_per_symbol[sym].select([
            "symbol", "event_time", pl.col("close").alias("perp_close"),
        ])
        spot_df = spot_df.select([
            "symbol", "event_time", pl.col("close").alias("spot_close"),
        ])
        funding_df = funding_per_symbol[sym].select(["symbol", "event_time", "funding_rate"])
        joined = (
            perp_df.join(spot_df, on=["symbol", "event_time"], how="inner")
            .sort("event_time")
            .join_asof(
                funding_df.sort("event_time"),
                on="event_time", by="symbol", strategy="backward",
            )
            .fill_null(0.0)
        )

        pnl_series, stats = _simulate_symbol(joined, cfg)
        # Apply maker-fill rate haircut to funding (selection bias)
        funding_collected = stats["funding"] * cfg.maker_fill_rate
        adjustment = stats["funding"] - funding_collected
        stats["funding"] = funding_collected
        pnl_series = pnl_series - (adjustment / max(len(pnl_series), 1))

        per_symbol_stats[sym] = stats
        times = joined["event_time"].cast(pl.Int64).to_numpy()
        for t, p in zip(times, pnl_series, strict=False):
            all_pnl_by_time[int(t)] = all_pnl_by_time.get(int(t), 0.0) + float(p)

    sorted_times = sorted(all_pnl_by_time.keys())
    pnl_arr = np.array([all_pnl_by_time[t] for t in sorted_times])
    equity = np.cumsum(pnl_arr)

    capital_base = cfg.notional_per_symbol_usd * len(deployed_symbols)
    returns = pnl_arr / capital_base if capital_base > 0 else np.zeros_like(pnl_arr)
    ts = tearsheet(returns, periods_per_year=int(cfg.annualization_hours), n_trials=1)

    total_funding = sum(s["funding"] for s in per_symbol_stats.values())
    total_basis = sum(s["basis"] for s in per_symbol_stats.values())
    total_fees = sum(s["fees"] for s in per_symbol_stats.values())
    total_entries = int(sum(s["n_entries"] for s in per_symbol_stats.values()))
    total_exits = int(sum(s["n_exits"] for s in per_symbol_stats.values()))
    avg_holds = [s["avg_hold"] for s in per_symbol_stats.values() if s["avg_hold"] > 0]
    avg_hold = float(np.mean(avg_holds)) if avg_holds else 0.0

    return A8Result(
        equity_curve=equity,
        cumulative_pnl_usd=float(equity[-1]) if len(equity) > 0 else 0.0,
        n_entries=total_entries,
        n_exits=total_exits,
        avg_hold_hours=avg_hold,
        funding_pnl_total=total_funding,
        basis_pnl_total=total_basis,
        fees_total=total_fees,
        tearsheet=ts,
        per_symbol_stats=per_symbol_stats,
    )
