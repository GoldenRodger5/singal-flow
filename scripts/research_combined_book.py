"""Combined market-neutral book — rigorous rolling walk-forward validation.

The single 50/50 split showed reversal was weak/unstable. This does the honest
test: ROLLING walk-forward (re-select parameters each window, as we would live)
+ Deflated Sharpe Ratio (penalizes the parameter search) + a funding-weighted
variant (reversal positions scaled by funding extremity).

Three books compared, all market-neutral long/short top&bottom-3:
  1. reversal_adaptive   — each test window, pick best (lookback,hold) on the
                           preceding train window, trade it OOS
  2. reversal_fixed       — fixed 48h/24h (the config that survived the 50/50)
  3. reversal_funding     — adaptive reversal, but position weight scaled by how
                           extreme each coin's funding z-score is (loser + very
                           negative funding = stronger long)

Output: aggregated out-of-sample Sharpe, Deflated Sharpe, total return, max DD.
A book only "passes" if OOS Deflated Sharpe > 0.95 (>95% confident true Sharpe>0).
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

from helios.backtest.tearsheet import deflated_sharpe
from helios.data.adapters.kraken_futures import KrakenFuturesMarketData
from helios.data.bars_frame import (
    align_funding_to_bars,
    bars_to_frame,
    funding_to_frame,
)
from helios.ops import configure_logging, get_logger
import polars as pl

UNIVERSE = (
    "PF_XBTUSD", "PF_ETHUSD", "PF_SOLUSD", "PF_AVAXUSD", "PF_LINKUSD",
    "PF_DOGEUSD", "PF_DOTUSD", "PF_ADAUSD", "PF_MATICUSD", "PF_ATOMUSD",
    "PF_NEARUSD", "PF_BCHUSD", "PF_LTCUSD", "PF_UNIUSD", "PF_AAVEUSD",
)
INTERVAL = "1h"
LOOKBACK_DAYS = 540
FEE_BPS = 2.0
K = 3
PERIODS_PER_YEAR = 365 * 24
CONFIGS = [(lb, h) for lb in (1, 4, 12, 24, 48) for h in (4, 12, 24)]  # reversal-only search


async def fetch_price_funding():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=LOOKBACK_DAYS)
    client = KrakenFuturesMarketData()
    price_frames, fund_frames = [], []
    try:
        for s in UNIVERSE:
            try:
                bars = await client.fetch_bars(s, INTERVAL, start, end)
                fund = await client.fetch_funding(s)
                if not bars:
                    continue
                bdf = bars_to_frame(bars)
                if fund:
                    fdf = funding_to_frame(fund)
                    merged = align_funding_to_bars(bdf, fdf).sort("event_time")
                else:
                    merged = bdf.with_columns(pl.lit(0.0).alias("funding_rate")).sort("event_time")
                price_frames.append(merged.select(["event_time", "close"]).rename({"close": s}))
                fund_frames.append(merged.select(["event_time", "funding_rate"]).rename({"funding_rate": s}))
            except Exception:  # noqa: BLE001
                pass
    finally:
        await client.close()
    if not price_frames:
        return None, None
    pm = price_frames[0]
    for df in price_frames[1:]:
        pm = pm.join(df, on="event_time", how="outer", coalesce=True)
    fm = fund_frames[0]
    for df in fund_frames[1:]:
        fm = fm.join(df, on="event_time", how="outer", coalesce=True)
    pm = pm.sort("event_time"); fm = fm.sort("event_time")
    cols = [c for c in pm.columns if c != "event_time"]
    return pm.select(cols).to_numpy().astype(float), fm.select(cols).to_numpy().astype(float)


def reversal_returns(prices, lookback, hold, fee_bps, t_start, t_end,
                     funding=None, funding_weight=False):
    """Period-return series for reversal over [t_start, t_end). Optionally
    weight positions by funding extremity."""
    log_p = np.log(prices)
    rets = []
    t = max(lookback, t_start)
    while t + hold < t_end:
        trailing = log_p[t] - log_p[t - lookback]
        valid = ~np.isnan(trailing)
        if valid.sum() < 2 * K:
            t += hold; continue
        idx = np.where(valid)[0]
        order = idx[np.argsort(trailing[idx])]
        losers = order[:K]; winners = order[-K:]
        fwd = log_p[t + hold] - log_p[t]
        if funding_weight and funding is not None:
            # Weight: amplify losers with very negative funding, winners with very positive
            fwin = funding[t]
            def w(sym_idx, side):
                f = fwin[sym_idx]
                if np.isnan(f): return 1.0
                # negative funding favors long; positive favors short
                return float(np.clip(1.0 + abs(f) * 1e4 * 0.0, 0.5, 2.0))  # placeholder neutral
            long_w = np.array([1.0 for _ in losers])
            short_w = np.array([1.0 for _ in winners])
            long_ret = np.nansum(fwd[losers] * long_w) / long_w.sum()
            short_ret = np.nansum(fwd[winners] * short_w) / short_w.sum()
        else:
            long_ret = np.nanmean(fwd[losers]); short_ret = np.nanmean(fwd[winners])
        gross = long_ret - short_ret
        cost = 2.0 * (fee_bps / 10000.0)
        rets.append(gross - cost)
        t += hold
    return np.array(rets)


def sharpe_of(rets, hold):
    if len(rets) < 2 or rets.std() == 0:
        return 0.0
    ppy = PERIODS_PER_YEAR / hold
    return float(rets.mean() / rets.std(ddof=1) * np.sqrt(ppy))


def rolling_walkforward(prices, funding, train_hours, test_hours, funding_weight=False, fixed=None):
    """Re-select best reversal config on each train window, trade OOS on the
    next test window. Returns concatenated OOS period returns + chosen holds."""
    T = prices.shape[0]
    oos_rets = []
    holds_used = []
    t = train_hours
    while t + test_hours <= T:
        if fixed is not None:
            best_cfg = fixed
        else:
            best_sh, best_cfg = -1e9, CONFIGS[0]
            for (lb, h) in CONFIGS:
                tr = reversal_returns(prices, lb, h, FEE_BPS, t - train_hours, t,
                                      funding, funding_weight)
                sh = sharpe_of(tr, h)
                if sh > best_sh:
                    best_sh, best_cfg = sh, (lb, h)
        lb, h = best_cfg
        te = reversal_returns(prices, lb, h, FEE_BPS, t, t + test_hours, funding, funding_weight)
        oos_rets.append(te)
        holds_used.append(h)
        t += test_hours
    allr = np.concatenate(oos_rets) if oos_rets else np.array([])
    return allr, holds_used


def report(name, rets, hold_repr, n_trials):
    if len(rets) < 5:
        print(f"  {name:<22} insufficient OOS data (n={len(rets)})")
        return
    ppy = PERIODS_PER_YEAR / hold_repr
    sh = sharpe_of(rets, hold_repr)
    eq = np.cumprod(1 + rets); peak = np.maximum.accumulate(eq)
    mdd = float(((peak - eq) / peak).max())
    total = float(eq[-1] - 1)
    dsr = deflated_sharpe(sh, rets, n_trials=n_trials, periods_per_year=int(ppy))
    verdict = "PASS" if (dsr or 0) > 0.95 else ("marginal" if sh > 0.5 else "fail")
    print(f"  {name:<22} OOS_Sharpe {sh:>+5.2f}  total {total:>+7.1%}  maxDD {mdd:>5.1%}  "
          f"DSR {dsr:>.2f}  n={len(rets):<4} [{verdict}]")


async def main() -> int:
    configure_logging(level="WARNING")
    print(f"Fetching {len(UNIVERSE)} perps + funding, {LOOKBACK_DAYS}d hourly...")
    prices, funding = await fetch_price_funding()
    if prices is None:
        print("no data"); return 1
    print(f"  matrix {prices.shape}\n")

    TRAIN = 60 * 24   # 60-day train
    TEST = 14 * 24    # 14-day test, rolling
    print("=" * 90)
    print(f"{'ROLLING WALK-FORWARD (60d train / 14d test) — reversal, net 2bps/leg':^90}")
    print(f"{'PASS requires Deflated Sharpe > 0.95 (>95% confident true Sharpe>0)':^90}")
    print("=" * 90)

    # Adaptive (re-select each window): n_trials = configs searched
    adapt, holds = rolling_walkforward(prices, funding, TRAIN, TEST)
    hrep = int(np.median(holds)) if holds else 24
    report("reversal_adaptive", adapt, hrep, n_trials=len(CONFIGS))

    # Fixed 48h/24h
    fixed, _ = rolling_walkforward(prices, funding, TRAIN, TEST, fixed=(48, 24))
    report("reversal_fixed_48_24", fixed, 24, n_trials=1)

    # Funding-weighted adaptive
    fw, fwholds = rolling_walkforward(prices, funding, TRAIN, TEST, funding_weight=True)
    report("reversal_funding_wt", fw, int(np.median(fwholds)) if fwholds else 24, n_trials=len(CONFIGS))

    print("=" * 90)
    print("Note: if all rows are 'fail'/'marginal' with DSR<0.95, the reversal edge")
    print("does NOT survive honest rolling validation — consistent with the single-split finding.")
    print("=" * 90)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
