"""Event-driven backtest engine.

Replays historical bars through the same orchestrator that runs live. This is
the critical property: if a strategy works in backtest, the only difference
when promoting it to paper or live is the data source — every other code path
is identical.

Usage:
    engine = BacktestEngine(strategies=[A1PerpTrend()], starting_cash=Decimal("1000"))
    bars = load_historical_bars(...)
    report = await engine.run(bars)
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timezone
from decimal import Decimal

import numpy as np

from helios.backtest.tearsheet import TearSheet, tearsheet
from helios.data.adapters import Bar
from helios.execution.paper_broker import MarketSnapshot, PaperBroker
from helios.execution.router import ExecutionMode, ExecutionRouter
from helios.ops import get_logger
from helios.orchestrator import Orchestrator
from helios.strategies import Strategy
from helios.types import Fill, PortfolioState, Position, Venue

log = get_logger(__name__)


@dataclass
class BacktestReport:
    fills: list[Fill]
    equity_curve: list[Decimal]
    tearsheet: TearSheet


@dataclass
class BacktestEngine:
    strategies: list[Strategy]
    starting_cash: Decimal = Decimal("1000")
    bar_spread_bps: float = 5.0  # default assumed spread; overridable via Bar metadata later
    periods_per_year: int = 365 * 24  # hourly bars on crypto by default

    async def run(self, bars: list[Bar]) -> BacktestReport:
        broker = PaperBroker(starting_cash=self.starting_cash)
        router = ExecutionRouter(mode=ExecutionMode.PAPER, paper=broker)
        orch = Orchestrator(strategies=self.strategies, router=router)
        await orch.prepare()

        # Group bars by (symbol, event_time) into time-ordered ticks
        bars_by_time: dict[tuple, list[Bar]] = defaultdict(list)
        for b in bars:
            bars_by_time[b.event_time].append(b)
        time_order = sorted(bars_by_time.keys())

        equity_curve: list[Decimal] = []
        peak_nav = self.starting_cash
        symbols = tuple({b.symbol for b in bars})

        for t in time_order:
            tick_bars = bars_by_time[t]
            snapshots: dict[tuple[str, Venue], MarketSnapshot] = {}
            marks: dict[tuple[str, Venue], Decimal] = {}
            for b in tick_bars:
                key = (b.symbol, b.venue)
                mid = (b.high + b.low) / Decimal("2")
                snapshots[key] = MarketSnapshot(
                    mid_price=mid,
                    spread_bps=self.bar_spread_bps,
                    bar_volume=float(b.volume),
                    bar_volatility=float((b.high - b.low) / mid) if mid > 0 else 0.0,
                )
                marks[key] = b.close

            nav = broker.nav(marks)
            peak_nav = max(peak_nav, nav)
            equity_curve.append(nav)

            state = PortfolioState(
                nav_usd=nav,
                peak_nav_usd=peak_nav,
                cash_usd=broker.cash,
                positions=tuple(_books_to_positions(broker)),
                open_orders=(),
                realized_pnl_today_usd=Decimal("0"),  # TODO: track via window
                realized_pnl_week_usd=Decimal("0"),
                realized_pnl_month_usd=Decimal("0"),
                as_of=t if t.tzinfo else t.replace(tzinfo=timezone.utc),
            )
            await orch.tick(state, snapshots, universe=symbols)

        returns = _equity_to_returns(equity_curve)
        ts = tearsheet(returns, periods_per_year=self.periods_per_year, n_trials=1)
        log.info(
            "backtest_done",
            n_bars=len(bars),
            n_fills=len(broker.fills),
            final_nav=str(equity_curve[-1] if equity_curve else self.starting_cash),
            sharpe=ts.sharpe,
            max_dd=ts.max_drawdown,
        )
        return BacktestReport(fills=broker.fills, equity_curve=equity_curve, tearsheet=ts)


def _books_to_positions(broker: PaperBroker) -> list[Position]:
    out: list[Position] = []
    for (symbol, venue), book in broker.positions.items():
        if book.qty == 0:
            continue
        from datetime import datetime
        out.append(Position(
            symbol=symbol,
            venue=venue,
            side=__import__("helios.types", fromlist=["Side"]).Side.LONG if book.qty > 0 else __import__("helios.types", fromlist=["Side"]).Side.SHORT,
            qty=abs(book.qty),
            avg_entry=book.avg_price,
            unrealized_pnl_usd=Decimal("0"),
            realized_pnl_usd=book.realized_pnl,
            leverage=1.0,
            opened_at=datetime.now(timezone.utc),
        ))
    return out


def _equity_to_returns(equity: list[Decimal]) -> np.ndarray:
    if len(equity) < 2:
        return np.array([])
    arr = np.array([float(e) for e in equity], dtype=float)
    rets = np.diff(arr) / arr[:-1]
    rets = np.nan_to_num(rets, nan=0.0, posinf=0.0, neginf=0.0)
    return rets
