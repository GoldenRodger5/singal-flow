"""Cross-sectional reversal/momentum research on the Kraken perp basket.

Thesis (reversal): crypto short-horizon returns mean-revert. Each rebalance,
rank the basket by trailing return; LONG the recent losers, SHORT the recent
winners, equal-weight, market-neutral. No directional bet, no fast execution,
regime-agnostic. The opposite sign (momentum) is also tested.

Why this is structurally different from A1/A2/A8 (all failed):
  - Market-neutral: doesn't care if crypto goes up or down
  - Relative, not absolute: never needs to predict WHICH coin moons
  - Slow: hourly/daily rebalance, maker fills, no latency race
  - Regime-agnostic: dispersion exists in bull, bear, and chop

Backtest:
  - Fetch hourly bars for the 15-perp universe
  - Build aligned log-return matrix
  - Grid over (lookback L, hold H, sign) — long-short top/bottom 3
  - Net of maker fees (2 bps/leg Kraken Futures) on rebalance turnover
  - Report annualized Sharpe, return, max DD, win rate per config
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import polars as pl

from helios.data.adapters.kraken_futures import KrakenFuturesMarketData
from helios.data.bars_frame import bars_to_frame
from helios.ops import configure_logging, get_logger

UNIVERSE = (
    "PF_XBTUSD", "PF_ETHUSD", "PF_SOLUSD", "PF_AVAXUSD", "PF_LINKUSD",
    "PF_DOGEUSD", "PF_DOTUSD", "PF_ADAUSD", "PF_MATICUSD", "PF_ATOMUSD",
    "PF_NEARUSD", "PF_BCHUSD", "PF_LTCUSD", "PF_UNIUSD", "PF_AAVEUSD",
)
INTERVAL = "1h"
LOOKBACK_DAYS = 540
PERP_FEE_BPS = 2.0          # Kraken Futures maker
K = 3                        # long bottom-K, short top-K
PERIODS_PER_YEAR = 365 * 24


async def fetch_matrix(symbols, days):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    log = get_logger("xsec")
    client = KrakenFuturesMarketData()
    frames = []
    try:
        for s in symbols:
            try:
                bars = await client.fetch_bars(s, INTERVAL, start, end)
                if bars:
                    df = bars_to_frame(bars).select(["event_time", "close"]).rename({"close": s})
                    frames.append(df)
            except Exception:  # noqa: BLE001
                pass
    finally:
        await client.close()
    if not frames:
        return None
    # Join all on event_time
    mat = frames[0]
    for df in frames[1:]:
        mat = mat.join(df, on="event_time", how="outer", coalesce=True)
    mat = mat.sort("event_time")
    return mat


def backtest_xsec(prices: np.ndarray, lookback: int, hold: int, sign: int, fee_bps: float) -> dict:
    """prices: (T, N) array of close prices (NaN where missing).
    sign=+1 momentum (long winners), sign=-1 reversal (long losers).
    Returns dict of metrics."""
    T, N = prices.shape
    log_p = np.log(prices)
    port_returns: list[float] = []
    t = lookback
    while t + hold < T:
        trailing = log_p[t] - log_p[t - lookback]          # trailing return per symbol
        valid = ~np.isnan(trailing)
        if valid.sum() < 2 * K:
            t += hold
            continue
        idx = np.where(valid)[0]
        order = idx[np.argsort(trailing[idx])]              # ascending: losers first
        losers = order[:K]
        winners = order[-K:]
        # Forward return over the holding period
        fwd = log_p[t + hold] - log_p[t]
        # reversal (sign=-1): long losers, short winners
        long_set = losers if sign < 0 else winners
        short_set = winners if sign < 0 else losers
        long_ret = np.nanmean(fwd[long_set])
        short_ret = np.nanmean(fwd[short_set])
        gross = long_ret - short_ret
        # Turnover cost: full rebalance = 2*K legs in + 2*K legs out per period
        # Approximate cost per period: 2 sides * fee (entry) — exit folds into next entry
        cost = 2.0 * (fee_bps / 10000.0)
        port_returns.append(gross - cost)
        t += hold
    if not port_returns:
        return {"n": 0}
    r = np.array(port_returns)
    # Annualize: each period is `hold` hours
    periods_per_year = PERIODS_PER_YEAR / hold
    mean_p = r.mean()
    std_p = r.std(ddof=1) if len(r) > 1 else 0.0
    sharpe = (mean_p / std_p * np.sqrt(periods_per_year)) if std_p > 0 else 0.0
    equity = np.cumprod(1 + r)
    peak = np.maximum.accumulate(equity)
    mdd = float(((peak - equity) / peak).max()) if len(equity) else 0.0
    total = float(equity[-1] - 1) if len(equity) else 0.0
    return {
        "n": len(r), "sharpe": float(sharpe), "total_return": total,
        "max_dd": mdd, "mean_per_period": float(mean_p),
        "win_rate": float((r > 0).mean()),
    }


async def main() -> int:
    configure_logging(level="WARNING")
    print(f"Fetching {len(UNIVERSE)} perps, {LOOKBACK_DAYS}d hourly...")
    mat = await fetch_matrix(UNIVERSE, LOOKBACK_DAYS)
    if mat is None:
        print("no data")
        return 1
    cols = [c for c in mat.columns if c != "event_time"]
    prices = mat.select(cols).to_numpy().astype(float)
    print(f"  matrix: {prices.shape[0]} timestamps x {prices.shape[1]} symbols\n")

    print("=" * 88)
    print(f"{'CROSS-SECTIONAL GRID — long/short top&bottom 3, net 2bps/leg maker':^88}")
    print("=" * 88)
    print(f"{'sign':>9}{'lookback':>9}{'hold':>6}{'n':>6}{'sharpe':>9}{'tot_ret':>10}{'maxDD':>8}{'win%':>7}")
    print("-" * 88)

    best = None
    for sign, label in [(-1, "reversal"), (1, "momentum")]:
        for lookback in (1, 4, 12, 24, 48):
            for hold in (1, 4, 12, 24):
                m = backtest_xsec(prices, lookback, hold, sign, PERP_FEE_BPS)
                if m.get("n", 0) < 20:
                    continue
                print(f"{label:>9}{lookback:>9}{hold:>6}{m['n']:>6}{m['sharpe']:>+9.2f}"
                      f"{m['total_return']:>+9.1%}{m['max_dd']:>7.1%}{m['win_rate']:>6.1%}")
                if best is None or m["sharpe"] > best[1]["sharpe"]:
                    best = ((label, lookback, hold), m)

    print("=" * 88)
    if best:
        (lbl, lb, h), m = best
        print(f"BEST: {lbl} lookback={lb}h hold={h}h → Sharpe {m['sharpe']:+.2f}, "
              f"total {m['total_return']:+.1%}, maxDD {m['max_dd']:.1%}, win {m['win_rate']:.1%}")
        print()
        if m["sharpe"] > 1.5:
            print("VERDICT: Promising. Sharpe > 1.5 net of maker fees on a market-neutral book.")
            print("  Next: walk-forward validate, add funding cost, check capacity at $1k.")
        elif m["sharpe"] > 0.5:
            print("VERDICT: Marginal. Some edge but not enough to deploy without more work.")
        else:
            print("VERDICT: No usable cross-sectional edge in this basket/window.")
    print("=" * 88)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
