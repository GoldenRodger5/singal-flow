"""A1 stress test — locked at horizon=1h after the prior sweep.

Pre-registered analysis sequence (no more search):
  1. Gross (no costs, no vol-target)            — sanity reference
  2. Net of costs (6 bps per fill)               — does edge survive friction?
  3. Net of costs + vol-target                   — does DD compress?
  4. Cross-symbol generalization                 — train BTC+ETH, test SOL,
                                                   AND time-OOS (older→newer)

Each result is one trial. We do NOT re-sweep horizons. We do NOT re-tune the
threshold. The signal either holds or it doesn't.

Run:  python -m scripts.backtest_a1
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import polars as pl

from helios.data.adapters.kraken_futures import KrakenFuturesMarketData
from helios.data.bars_frame import align_funding_to_bars, bars_to_frame, funding_to_frame
from helios.ops import configure_logging, get_logger
from helios.strategies.a1_perp_trend.features import compute_features
from helios.strategies.a1_perp_trend.train import (
    TrainResult,
    train_a1,
    train_a1_cross_symbol,
)

SYMBOLS = ["PF_XBTUSD", "PF_ETHUSD", "PF_SOLUSD"]
INTERVAL = "1h"
LOOKBACK_DAYS = 540
HORIZON = 1  # LOCKED
N_SPLITS = 5
VAL_SIZE = 200
MIN_TRAIN_SIZE = 1000
COST_BPS_PER_FILL = 6.0    # 5 bps taker + ~1 bps half-spread, conservative
TARGET_VOL_PER_BAR = 0.008  # 80 bps hourly target vol -> ~12% annualized

COMPUTED_FEATURES = [
    "ret_1", "ret_5", "ret_20", "vol_20",
    "vol_zscore_20_vs_60", "momentum_zscore_20", "volume_ratio_5_vs_60",
    "funding_zscore_24",
]


async def fetch_all(symbols: list[str], interval: str, days: int) -> pl.DataFrame:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    log = get_logger("fetch")
    client = KrakenFuturesMarketData()
    try:
        bar_frames: list[pl.DataFrame] = []
        fund_frames: list[pl.DataFrame] = []
        for symbol in symbols:
            bars = await client.fetch_bars(symbol, interval, start, end)
            funding = await client.fetch_funding(symbol)
            log.info("fetched", symbol=symbol, bars=len(bars), funding=len(funding))
            bar_frames.append(bars_to_frame(bars))
            fund_frames.append(funding_to_frame(funding))
    finally:
        await client.close()
    bars_df = pl.concat(bar_frames).sort(["symbol", "event_time"])
    fund_df = pl.concat(fund_frames).sort(["symbol", "event_time"])
    return align_funding_to_bars(bars_df, fund_df)


def print_result(name: str, r: TrainResult, n_trials: int) -> None:
    ts = r.oos_tearsheet
    dsr = f"{ts.deflated_sharpe:.3f}" if ts.deflated_sharpe is not None else "n/a"
    print("\n" + "=" * 70)
    print(f"{name:^70}")
    print("=" * 70)
    print(f"OOS bars:                 {ts.n_periods:>10,}")
    print(f"Trades:                   {r.n_trades:>10,}    transitions: {r.n_transitions:.0f}")
    print(f"Trade hit rate:           {r.trade_hit_rate:>10.2%}")
    print(f"Win/loss ratio:           {ts.win_loss_ratio:>10.3f}")
    print(f"Sharpe (annualized):      {ts.sharpe:>10.3f}")
    print(f"Sortino:                  {ts.sortino:>10.3f}")
    print(f"Max drawdown:             {ts.max_drawdown:>10.2%}")
    print(f"CAGR:                     {ts.cagr:>10.2%}")
    print(f"Total return:             {ts.total_return:>10.2%}")
    print(f"Gross mean return/bar:    {r.gross_return_mean*10000:>10.2f} bps")
    print(f"Cost drag/bar:            {r.cost_drag_per_bar_bps:>10.2f} bps")
    print(f"Deflated Sharpe (n={n_trials}):  {dsr}")
    print("=" * 70)


def verdict(name: str, r: TrainResult) -> str:
    ts = r.oos_tearsheet
    dsr = ts.deflated_sharpe or 0.0
    if ts.sharpe > 1.0 and ts.max_drawdown < 0.20 and dsr > 0.95:
        return f"  → {name}: PASSES gate (Sharpe>1, DD<20%, DSR>0.95). Promote to paper."
    if ts.sharpe > 0.5 and dsr > 0.8:
        return f"  → {name}: PROMISING but DSR={dsr:.2f} too low to deploy. More data needed."
    if ts.sharpe > 0:
        return f"  → {name}: Marginal positive, but Sharpe={ts.sharpe:.2f} too thin to risk."
    return f"  → {name}: FAILS gate. Signal does not survive this filter."


async def main() -> int:
    configure_logging(level="WARNING")  # quiet xgboost / train info logs for the summary
    print("Fetching Kraken Futures bars + funding...")
    merged = await fetch_all(SYMBOLS, INTERVAL, LOOKBACK_DAYS)
    print(f"  {merged.height:,} rows, {merged['symbol'].n_unique()} symbols, "
          f"{merged['event_time'].min()} → {merged['event_time'].max()}")
    print(f"  bars with funding attached: {int(merged['funding_rate'].is_not_null().sum()):,}")

    feat = compute_features(merged)
    feat = feat.join(
        merged.select(["symbol", "event_time", "close"]),
        on=["symbol", "event_time"], how="left",
    ).drop_nulls(subset=[*COMPUTED_FEATURES, "close"])
    print(f"  feature rows: {feat.height:,}\n")

    print(f"LOCKED horizon: {HORIZON}h. Threshold 0.55. n_trials counts each scenario below as 1.\n")

    # ----- 1. Gross reference (no costs, no vol-target) -----
    r_gross = train_a1(
        feat, horizon=HORIZON,
        n_splits=N_SPLITS, val_size=VAL_SIZE, min_train_size=MIN_TRAIN_SIZE,
        n_trials=4, apply_costs=False, target_vol_per_bar=None,
    )
    print_result("(1) GROSS reference (no costs, no vol-target)", r_gross, n_trials=4)

    # ----- 2. Net of costs (no vol-target) -----
    r_net = train_a1(
        feat, horizon=HORIZON,
        n_splits=N_SPLITS, val_size=VAL_SIZE, min_train_size=MIN_TRAIN_SIZE,
        n_trials=4, apply_costs=True, cost_bps_per_fill=COST_BPS_PER_FILL,
        target_vol_per_bar=None,
    )
    print_result(f"(2) NET of costs ({COST_BPS_PER_FILL} bps/fill)", r_net, n_trials=4)

    # ----- 3. Net + vol-target -----
    r_voltarget = train_a1(
        feat, horizon=HORIZON,
        n_splits=N_SPLITS, val_size=VAL_SIZE, min_train_size=MIN_TRAIN_SIZE,
        n_trials=4, apply_costs=True, cost_bps_per_fill=COST_BPS_PER_FILL,
        target_vol_per_bar=TARGET_VOL_PER_BAR,
    )
    print_result(f"(3) NET + VOL-TARGET ({TARGET_VOL_PER_BAR*10000:.0f}bps/bar)", r_voltarget, n_trials=4)

    # ----- 4. Cross-symbol generalization (train BTC+ETH, test SOL) -----
    try:
        r_xsym = train_a1_cross_symbol(
            feat,
            train_symbols=["PF_XBTUSD", "PF_ETHUSD"],
            test_symbols=["PF_SOLUSD"],
            horizon=HORIZON,
            apply_costs=True,
            cost_bps_per_fill=COST_BPS_PER_FILL,
            target_vol_per_bar=TARGET_VOL_PER_BAR,
        )
        print_result("(4) CROSS-SYMBOL — train BTC+ETH, test SOL (time-OOS)", r_xsym, n_trials=4)
    except ValueError as e:
        print(f"\n(4) CROSS-SYMBOL skipped: {e}")
        r_xsym = None

    # ----- Final summary -----
    print("\n" + "=" * 70)
    print(f"{'FINAL VERDICTS (locked horizon = 1h, threshold = 0.55)':^70}")
    print("=" * 70)
    print(verdict("(1) gross", r_gross))
    print(verdict("(2) net of costs", r_net))
    print(verdict("(3) net + vol-target", r_voltarget))
    if r_xsym is not None:
        print(verdict("(4) cross-symbol + time-OOS", r_xsym))
    print()

    # Bottom-line judgment
    nets = [r_net, r_voltarget] + ([r_xsym] if r_xsym else [])
    if all(r.oos_tearsheet.sharpe < 0 for r in nets):
        print("Bottom line: A1 with this feature set has no edge after costs. Recommendation:")
        print("  • Move A1 to backlog (don't delete — the data plane is useful for other strategies).")
        print("  • Stand up A8 (cash-and-carry funding harvest) next — deterministic, math-based, no prediction.")
    elif r_xsym and r_xsym.oos_tearsheet.sharpe > 0.5:
        print("Bottom line: A1 may have a real cross-symbol signal. Concrete next step:")
        print("  • Fetch 2-3 years of history from a longer-history source (Coinbase spot).")
        print("  • Re-run cross-symbol test on the extended dataset (one trial).")
        print("  • If DSR > 0.95, promote to 30-day paper trade on $200 notional.")
    else:
        print("Bottom line: marginal at best. Iteration options (each is ONE more trial — track them):")
        print("  • Funding-direction interaction feature (sign(funding) * momentum)")
        print("  • Multi-timeframe momentum (1h + 4h + 24h ensemble)")
        print("  • Longer history before any more feature engineering.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
