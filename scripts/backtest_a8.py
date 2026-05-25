"""A8 cash-and-carry backtest on real Kraken data.

Pre-registered scenarios (each = one trial; we report all and apply DSR penalty):
  S1  Default thresholds (entry 8% APY, exit 2% APY)
  S2  Tighter entry (12% APY) — only harvest in clearly-elevated regimes
  S3  Maker-fee variant of S1 (16 bps spot, 2 bps perp) — limit-order entries

Output: net cumulative USD P&L on $750 deployed capital ($250/symbol × 3 symbols),
plus realized annualized yield and Sharpe.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import polars as pl

from helios.data.adapters.kraken_futures import KrakenFuturesMarketData
from helios.data.bars_frame import bars_to_frame, funding_to_frame
from helios.ops import configure_logging, get_logger
from helios.strategies.a8_cash_carry import A8Config, backtest_a8

PERPS = ["PF_XBTUSD", "PF_ETHUSD", "PF_SOLUSD"]
INTERVAL = "1h"
LOOKBACK_DAYS = 540


async def fetch_all(perps: list[str], days: int):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    log = get_logger("fetch")

    fut_client = KrakenFuturesMarketData()
    perp_frames: list[pl.DataFrame] = []
    fund_frames: list[pl.DataFrame] = []
    try:
        for sym in perps:
            pbars = await fut_client.fetch_bars(sym, INTERVAL, start, end)
            funding = await fut_client.fetch_funding(sym)
            log.info("fetched", symbol=sym, perp_bars=len(pbars), funding=len(funding))
            perp_frames.append(bars_to_frame(pbars))
            fund_frames.append(funding_to_frame(funding))
    finally:
        await fut_client.close()

    perp_df = pl.concat(perp_frames).sort(["symbol", "event_time"])
    # SPOT ≈ PERP approximation (basis P&L treated as zero). Kraken Spot public
    # OHLC only returns ~30 days of hourly history regardless of `since`, so for
    # the 15-month backtest we approximate. On liquid majors the basis is small
    # (typically < 30 bps). When A8 passes this gate we'll re-validate with
    # Coinbase Advanced spot history which has multi-year reach.
    spot_df = perp_df
    fund_df = pl.concat(fund_frames).sort(["symbol", "event_time"])
    return perp_df, spot_df, fund_df


def print_report(name: str, cfg: A8Config, result, capital_base: float) -> None:
    ts = result.tearsheet
    annual_yield = result.cumulative_pnl_usd / capital_base * (8760 / max(ts.n_periods, 1))
    print("\n" + "=" * 70)
    print(f"{name:^70}")
    print("=" * 70)
    print(f"Deployed capital:         ${capital_base:>10,.2f}")
    print(f"Cumulative P&L:           ${result.cumulative_pnl_usd:>10,.2f}")
    print(f"   funding payments:      ${result.funding_pnl_total:>10,.2f}")
    print(f"   basis drift:           ${result.basis_pnl_total:>10,.2f}")
    print(f"   fees:                  ${-result.fees_total:>10,.2f}")
    print(f"Realized annual yield:    {annual_yield:>10.2%}")
    print(f"Sharpe (annualized):      {ts.sharpe:>10.3f}")
    print(f"Sortino:                  {ts.sortino:>10.3f}")
    print(f"Max drawdown:             {ts.max_drawdown:>10.2%}")
    print(f"Entries / exits:          {result.n_entries:>10d}  /  {result.n_exits}")
    print(f"Avg hold (hours):         {result.avg_hold_hours:>10.1f}")
    print(f"Deflated Sharpe (n=3):    {ts.deflated_sharpe!r}")
    print("\nPer-symbol breakdown:")
    print(f"  {'symbol':<14} {'entries':>8} {'funding':>10} {'basis':>10} {'fees':>10}")
    for sym, s in result.per_symbol_stats.items():
        print(f"  {sym:<14} {int(s['n_entries']):>8d} {s['funding']:>10.2f} {s['basis']:>10.2f} {s['fees']:>10.2f}")
    print("=" * 70)


async def main() -> int:
    configure_logging(level="WARNING")
    print("Fetching Kraken Futures perps + Kraken Spot + funding history...")
    perp_df, spot_df, fund_df = await fetch_all(PERPS, LOOKBACK_DAYS)
    print(f"  perp: {perp_df.height:,} rows   spot: {spot_df.height:,} rows   funding: {fund_df.height:,} rows")
    print(f"  date range: {perp_df['event_time'].min()} → {perp_df['event_time'].max()}\n")

    print("Pre-registered scenarios:\n"
          "  S1  Default (entry 8% APY, exit 2% APY, taker fees)\n"
          "  S2  Tighter entry (entry 12% APY)\n"
          "  S3  Maker fees on S1\n")

    cfg1 = A8Config()
    cfg2 = A8Config(entry_apy=0.12)
    cfg3 = A8Config(spot_fee_bps=16.0, perp_fee_bps=2.0)

    r1 = backtest_a8(perp_df, spot_df, fund_df, cfg1)
    r2 = backtest_a8(perp_df, spot_df, fund_df, cfg2)
    r3 = backtest_a8(perp_df, spot_df, fund_df, cfg3)

    capital = cfg1.notional_per_symbol_usd * len(PERPS)
    print_report("S1 — DEFAULT (entry 8%, exit 2%, taker fees)", cfg1, r1, capital)
    print_report("S2 — TIGHTER ENTRY (entry 12%, exit 2%, taker)", cfg2, r2, capital)
    print_report("S3 — MAKER FEES (entry 8%, exit 2%, maker)", cfg3, r3, capital)

    print("\n" + "=" * 70)
    print(f"{'A8 SUMMARY':^70}")
    print("=" * 70)
    for name, r in [("S1", r1), ("S2", r2), ("S3", r3)]:
        ts = r.tearsheet
        annual = r.cumulative_pnl_usd / capital * (8760 / max(ts.n_periods, 1))
        print(f"  {name}: pnl ${r.cumulative_pnl_usd:>+8.2f}  ann.yld {annual:>+7.2%}  "
              f"Sharpe {ts.sharpe:>+6.2f}  MaxDD {ts.max_drawdown:>5.2%}")

    print("\nInterpretation guide:")
    print("  • Net annual yield is the headline. Even 5-10% APY at near-zero correlation")
    print("    to crypto direction is a real result on $1k.")
    print("  • If Sharpe > 2 and MaxDD < 5%, A8 is the ballast strategy of the book.")
    print("  • Fees dominating funding = need bigger position size OR longer holds OR maker.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
