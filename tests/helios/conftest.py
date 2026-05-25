"""Shared test fixtures for helios tests."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from helios.types import (
    Intent,
    PortfolioState,
    Side,
    Signal,
    StrategyId,
    Venue,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def fresh_state() -> PortfolioState:
    """$1k account, no positions, no losses, no drawdown."""
    return PortfolioState(
        nav_usd=Decimal("1000"),
        peak_nav_usd=Decimal("1000"),
        cash_usd=Decimal("1000"),
        positions=(),
        open_orders=(),
        realized_pnl_today_usd=Decimal("0"),
        realized_pnl_week_usd=Decimal("0"),
        realized_pnl_month_usd=Decimal("0"),
        as_of=_now(),
    )


@pytest.fixture
def base_signal() -> Signal:
    return Signal(
        strategy=StrategyId.A1_PERP_TREND,
        symbol="BTC-PERP",
        venue=Venue.KRAKEN_FUTURES,
        direction=1,
        magnitude=0.6,
        confidence=0.65,
        confidence_lower=0.02,
        invalidation_price=Decimal("100"),
        target_price=Decimal("106"),
        features_hash="abc123",
        created_at=_now(),
    )


@pytest.fixture
def base_intent(base_signal: Signal) -> Intent:
    return Intent(
        strategy=StrategyId.A1_PERP_TREND,
        symbol="BTC-PERP",
        venue=Venue.KRAKEN_FUTURES,
        side=Side.LONG,
        notional_usd=Decimal("200"),
        leverage=3.0,
        stop_price=Decimal("98"),
        take_profit_price=Decimal("106"),
        signal_ref=base_signal,
    )
