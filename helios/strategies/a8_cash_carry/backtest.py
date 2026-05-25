"""A8 backtest — vectorized hourly P&L for cash-and-carry on Kraken Futures.

Inputs (Polars frames, hourly aligned per symbol):
    perp:    symbol, event_time, close (perp mark)
    spot:    symbol, event_time, close (spot mark)
    funding: symbol, event_time, funding_rate (relative-per-hour, signed)

Position model per symbol:
    state ∈ {0 = flat, 1 = long-spot/short-perp}
    Notional = position_size_usd (constant when open)

Hourly P&L when long_basis open at hour t:
    funding_pnl_t  = funding_rate[t] × notional        (we collect from longs)
    basis_pnl_t    = - (perp_close[t] - perp_close[t-1])
                     + (spot_close[t] - spot_close[t-1])
                     ALL scaled by notional / perp_close[t-1]  (per-unit moves × N units)
    total_t        = funding_pnl_t + basis_pnl_t
    open/close cost = - notional × (spot_fee + perp_fee) at boundary hours

Entry/exit policy:
    Maintain trailing_mean over `signal_window` hours of annualized funding
    Enter if trailing > entry_apy and currently flat
    Exit  if trailing < exit_apy  (or trailing turns negative)

Tearsheet generated on the hourly equity series.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl

from helios.backtest.tearsheet import TearSheet, tearsheet


@dataclass
class A8Config:
    notional_per_symbol_usd: float = 250.0  # $250 per symbol → up to 3 × $250 = $750 from $1k NAV
    entry_apy: float = 0.08         # enter when trailing annualized funding > 8%
    exit_apy: float = 0.02          # exit when trailing < 2%
    signal_window_hours: int = 24   # trailing window for funding signal
    spot_fee_bps: float = 26.0      # Kraken Spot taker, low-volume retail
    perp_fee_bps: float = 5.0       # Kraken Futures taker
    annualization_hours: float = 8760.0  # hours per year (funding is hourly)


@dataclass
class A8Result:
    equity_curve: np.ndarray  # hourly equity, starting at 0 (P&L in USD)
    cumulative_pnl_usd: float
    n_entries: int
    n_exits: int
    avg_hold_hours: float
    funding_pnl_total: float
    basis_pnl_total: float
    fees_total: float
    tearsheet: TearSheet
    per_symbol_stats: dict[str, dict[str, float]] = field(default_factory=dict)


def _align(
    perp: pl.DataFrame, spot: pl.DataFrame, funding: pl.DataFrame
) -> pl.DataFrame:
    """Inner-join perp+spot bars on (symbol, event_time); asof-join funding."""
    perp = perp.select(["symbol", "event_time", pl.col("close").alias("perp_close")])
    spot = spot.select(["symbol", "event_time", pl.col("close").alias("spot_close")])
    joined = perp.join(spot, on=["symbol", "event_time"], how="inner").sort(["symbol", "event_time"])
    funding = funding.select(["symbol", "event_time", "funding_rate"]).sort(["symbol", "event_time"])
    joined = joined.sort("event_time").join_asof(
        funding.sort("event_time"), on="event_time", by="symbol", strategy="backward",
    )
    return joined.sort(["symbol", "event_time"]).fill_null(0.0)


def _simulate_symbol(
    df: pl.DataFrame, cfg: A8Config
) -> tuple[np.ndarray, dict[str, float]]:
    """Run the policy on a single symbol's joined frame. Return hourly P&L
    series (USD) and a per-symbol diagnostics dict.
    """
    df = df.sort("event_time")
    n = df.height
    if n < cfg.signal_window_hours + 2:
        return np.zeros(n), {"n_entries": 0, "n_exits": 0, "funding": 0.0, "basis": 0.0, "fees": 0.0, "avg_hold": 0.0}

    perp_close = df["perp_close"].to_numpy().astype(float)
    spot_close = df["spot_close"].to_numpy().astype(float)
    funding = df["funding_rate"].to_numpy().astype(float)

    # Trailing-mean annualized funding signal (causal)
    rolling = (
        df.with_columns(
            pl.col("funding_rate").rolling_mean(window_size=cfg.signal_window_hours).alias("_fr_mean")
        )["_fr_mean"]
        .to_numpy().astype(float)
    )
    annualized = rolling * cfg.annualization_hours
    annualized = np.nan_to_num(annualized, nan=0.0)

    state = 0  # 0 flat, 1 open
    n_entries = 0
    n_exits = 0
    funding_pnl = 0.0
    basis_pnl = 0.0
    fees_paid = 0.0
    hold_hours: list[int] = []
    open_at = -1

    pnl_series = np.zeros(n)
    fee_per_round_trip = cfg.notional_per_symbol_usd * (cfg.spot_fee_bps + cfg.perp_fee_bps) / 10000.0
    # Pay half on entry, half on exit
    fee_per_leg = fee_per_round_trip / 2.0

    for t in range(1, n):
        sig = annualized[t]
        if state == 0:
            if sig > cfg.entry_apy:
                # Enter at this hour. Pay entry fees. No P&L this hour beyond -fees.
                state = 1
                open_at = t
                fees_paid += fee_per_leg
                pnl_series[t] -= fee_per_leg
                n_entries += 1
        else:  # state == 1, position open
            # Funding payment for this hour (paid by longs to shorts when funding>0)
            # We are SHORT the perp -> we receive funding when funding_rate > 0.
            fp = funding[t] * cfg.notional_per_symbol_usd
            funding_pnl += fp

            # Basis P&L: change in (spot - perp) over the bar, per unit, times units.
            # Units bought = notional / entry_perp_price; for hourly mark-to-mark
            # simplification we use t-1 perp_close as the unit basis.
            if perp_close[t-1] > 0:
                units = cfg.notional_per_symbol_usd / perp_close[t-1]
                bp = (spot_close[t] - spot_close[t-1]) * units - (perp_close[t] - perp_close[t-1]) * units
            else:
                bp = 0.0
            basis_pnl += bp

            pnl_series[t] += fp + bp

            # Exit?
            if sig < cfg.exit_apy:
                fees_paid += fee_per_leg
                pnl_series[t] -= fee_per_leg
                hold_hours.append(t - open_at)
                state = 0
                open_at = -1
                n_exits += 1

    return pnl_series, {
        "n_entries": float(n_entries),
        "n_exits": float(n_exits),
        "funding": funding_pnl,
        "basis": basis_pnl,
        "fees": fees_paid,
        "avg_hold": float(np.mean(hold_hours)) if hold_hours else 0.0,
    }


def backtest_a8(
    perp_bars: pl.DataFrame,
    spot_bars: pl.DataFrame,
    funding: pl.DataFrame,
    cfg: A8Config | None = None,
) -> A8Result:
    cfg = cfg or A8Config()
    joined = _align(perp_bars, spot_bars, funding)

    per_symbol_stats: dict[str, dict[str, float]] = {}
    symbols = joined["symbol"].unique().to_list()
    all_pnl_by_time: dict[int, float] = {}

    for sym in symbols:
        sub = joined.filter(pl.col("symbol") == sym).sort("event_time")
        pnl_series, stats = _simulate_symbol(sub, cfg)
        per_symbol_stats[sym] = stats
        # Aggregate to portfolio P&L by event_time
        times = sub["event_time"].cast(pl.Int64).to_numpy()  # microseconds since epoch
        for t, p in zip(times, pnl_series, strict=False):
            all_pnl_by_time[int(t)] = all_pnl_by_time.get(int(t), 0.0) + float(p)

    # Build the aggregated equity series, sorted by time
    sorted_times = sorted(all_pnl_by_time.keys())
    pnl_arr = np.array([all_pnl_by_time[t] for t in sorted_times])
    equity = np.cumsum(pnl_arr)

    # Capital base for return calc: sum of all symbols' notionals (we approximate
    # NAV-required as this — the carry trade keeps cash equal to notional in spot).
    capital_base = cfg.notional_per_symbol_usd * len(symbols)

    # Hourly return on capital base
    if capital_base > 0:
        returns = pnl_arr / capital_base
    else:
        returns = np.zeros_like(pnl_arr)
    ts = tearsheet(returns, periods_per_year=int(cfg.annualization_hours), n_trials=1)

    total_funding = sum(s["funding"] for s in per_symbol_stats.values())
    total_basis = sum(s["basis"] for s in per_symbol_stats.values())
    total_fees = sum(s["fees"] for s in per_symbol_stats.values())
    total_entries = int(sum(s["n_entries"] for s in per_symbol_stats.values()))
    total_exits = int(sum(s["n_exits"] for s in per_symbol_stats.values()))
    avg_hold = float(np.mean([s["avg_hold"] for s in per_symbol_stats.values() if s["avg_hold"] > 0])) \
        if any(s["avg_hold"] > 0 for s in per_symbol_stats.values()) else 0.0

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
