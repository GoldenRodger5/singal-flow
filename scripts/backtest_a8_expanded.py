"""A8 expanded backtest — 15-perp universe with maker-only fee assumption.

Fetches Kraken Futures bars + funding for the expanded universe, runs the
A8 expanded backtest, prints the headline.

Run: python -m scripts.backtest_a8_expanded
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import polars as pl

from helios.data.adapters.kraken_futures import KrakenFuturesMarketData
from helios.data.bars_frame import bars_to_frame, funding_to_frame
from helios.ops import configure_logging, get_logger
from helios.strategies.a8_cash_carry.expanded import (
    EXPANDED_UNIVERSE,
    A8ExpandedConfig,
    backtest_a8_expanded,
)

INTERVAL = "1h"
LOOKBACK_DAYS = 540


async def fetch_universe(symbols, days):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    log = get_logger("a8_expanded_fetch")
    client = KrakenFuturesMarketData()
    perp_per: dict[str, pl.DataFrame] = {}
    fund_per: dict[str, pl.DataFrame] = {}
    try:
        for sym in symbols:
            try:
                pbars = await client.fetch_bars(sym, INTERVAL, start, end)
                fund = await client.fetch_funding(sym)
                if pbars and fund:
                    perp_per[sym] = bars_to_frame(pbars)
                    fund_per[sym] = funding_to_frame(fund)
                    log.info("fetched", symbol=sym, bars=len(pbars), funding=len(fund))
                else:
                    log.warning("no_data", symbol=sym)
            except Exception as e:  # noqa: BLE001
                log.warning("fetch_failed", symbol=sym, error=str(e))
    finally:
        await client.close()
    return perp_per, fund_per


async def main() -> int:
    configure_logging(level="WARNING")
    print(f"Fetching {len(EXPANDED_UNIVERSE)} Kraken Futures perps...")
    perp_per, fund_per = await fetch_universe(EXPANDED_UNIVERSE, LOOKBACK_DAYS)
    print(f"  Got data for {len(perp_per)} / {len(EXPANDED_UNIVERSE)} symbols")
    print()

    print("=" * 70)
    print(f"{'A8 EXPANDED BACKTEST':^70}")
    print(f"{'15 perps, maker-only (16/2 bps), entry 10% APY, exit 2%':^70}")
    print("=" * 70)

    cfg = A8ExpandedConfig()
    result = backtest_a8_expanded(perp_per, perp_per, fund_per, cfg)  # perp as spot proxy
    capital_base = cfg.notional_per_symbol_usd * len(perp_per)
    annual_yield = (result.cumulative_pnl_usd / capital_base) * (8760 / max(result.tearsheet.n_periods, 1))

    print(f"Deployed capital:         ${capital_base:>10,.2f}")
    print(f"Cumulative P&L:           ${result.cumulative_pnl_usd:>10,.2f}")
    print(f"   funding (× {cfg.maker_fill_rate:.0%} fill):  ${result.funding_pnl_total:>10,.2f}")
    print(f"   basis drift:           ${result.basis_pnl_total:>10,.2f}")
    print(f"   fees:                  ${-result.fees_total:>10,.2f}")
    print(f"Annualized yield:         {annual_yield:>10.2%}")
    print(f"Sharpe (annualized):      {result.tearsheet.sharpe:>10.3f}")
    print(f"Max drawdown:             {result.tearsheet.max_drawdown:>10.2%}")
    print(f"Entries / exits:          {result.n_entries:>10d}  /  {result.n_exits}")
    print(f"Avg hold (hours):         {result.avg_hold_hours:>10.1f}")
    print()
    print("Per-symbol funding income (top 10):")
    sorted_stats = sorted(result.per_symbol_stats.items(), key=lambda kv: -kv[1]["funding"])
    for sym, s in sorted_stats[:10]:
        print(f"  {sym:<14} funding=${s['funding']:>+8.2f}  fees=${s['fees']:>6.2f}  "
              f"entries={int(s['n_entries']):>3}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
