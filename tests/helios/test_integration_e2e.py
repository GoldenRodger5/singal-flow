"""End-to-end integration: stub strategy → orchestrator → risk → paper broker.

This is the smoke test that proves the spine compiles and runs deterministically.
A real strategy + real data lands in Phase 2; this test exercises the wiring
so structural regressions get caught on every commit.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from helios.backtest.engine import BacktestEngine
from helios.data.adapters import Bar
from helios.strategies.base import Strategy, StrategyContext
from helios.types import Signal, StrategyId, Venue


class _AlwaysLongStub(Strategy):
    """Emits a long signal on the first tick only. Stable target/stop for risk overlay."""
    id = StrategyId.A1_PERP_TREND
    _fired: bool = False

    async def prepare(self) -> None:
        self._fired = False

    async def evaluate(self, ctx: StrategyContext) -> list[Signal]:
        if self._fired:
            return []
        if not ctx.universe:
            return []
        self._fired = True
        return [Signal(
            strategy=self.id,
            symbol=ctx.universe[0],
            venue=Venue.KRAKEN_FUTURES,
            direction=1,
            magnitude=0.6,
            confidence=0.65,
            confidence_lower=0.03,
            invalidation_price=Decimal("98"),
            target_price=Decimal("105"),
            features_hash="stub",
            created_at=ctx.as_of,
        )]


def _synthetic_bars(n: int = 20, start_price: float = 100.0) -> list[Bar]:
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bars: list[Bar] = []
    p = start_price
    for i in range(n):
        t = t0 + timedelta(hours=i)
        # Gentle uptrend for a clean test
        new_p = p * 1.005
        bars.append(Bar(
            symbol="BTC-PERP",
            venue=Venue.KRAKEN_FUTURES,
            interval="1h",
            open=Decimal(str(p)),
            high=Decimal(str(max(p, new_p) * 1.001)),
            low=Decimal(str(min(p, new_p) * 0.999)),
            close=Decimal(str(new_p)),
            volume=Decimal("10000"),
            event_time=t,
            available_at=t,
        ))
        p = new_p
    return bars


@pytest.mark.asyncio
async def test_end_to_end_smoke():
    engine = BacktestEngine(strategies=[_AlwaysLongStub()], starting_cash=Decimal("1000"))
    bars = _synthetic_bars(n=30)
    report = await engine.run(bars)

    # At least one fill should have happened (the strategy fires on tick 1)
    assert len(report.fills) >= 1
    # Equity curve has one entry per tick
    assert len(report.equity_curve) == 30
    # Tearsheet is populated
    assert report.tearsheet.n_periods == 29  # diff() loses 1
