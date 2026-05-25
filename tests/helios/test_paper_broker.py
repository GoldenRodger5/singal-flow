"""Tests for the paper broker."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from helios.execution.paper_broker import MarketSnapshot, PaperBroker
from helios.types import (
    Intent,
    Order,
    Side,
    Signal,
    StrategyId,
    Venue,
)


def _mk_order(side: Side, qty: str, symbol: str = "BTC-PERP") -> Order:
    sig = Signal(
        strategy=StrategyId.A1_PERP_TREND,
        symbol=symbol, venue=Venue.KRAKEN_FUTURES, direction=1 if side == Side.LONG else -1,
        magnitude=0.5, confidence=0.6, confidence_lower=0.02,
        invalidation_price=Decimal("100"), target_price=Decimal("110"),
        features_hash="x", created_at=datetime.now(timezone.utc),
    )
    intent = Intent(
        strategy=StrategyId.A1_PERP_TREND, symbol=symbol, venue=Venue.KRAKEN_FUTURES,
        side=side, notional_usd=Decimal("100"), leverage=1.0,
        stop_price=Decimal("98"), take_profit_price=Decimal("110"), signal_ref=sig,
    )
    return Order(intent=intent, qty=Decimal(qty), order_type="market", limit_price=None,
                 client_order_id="o1", approved_at=datetime.now(timezone.utc))


@pytest.fixture
def broker():
    return PaperBroker(starting_cash=Decimal("1000"))


@pytest.fixture
def snap():
    return MarketSnapshot(mid_price=Decimal("100"), spread_bps=5.0, bar_volume=10000.0, bar_volatility=0.005)


def test_long_fill_deducts_cash(broker, snap):
    order = _mk_order(Side.LONG, "1")
    broker.submit(order, snap)
    assert broker.cash < Decimal("1000")


def test_long_then_short_realizes_pnl(broker):
    snap_in = MarketSnapshot(mid_price=Decimal("100"), spread_bps=1.0, bar_volume=10000.0, bar_volatility=0.0)
    snap_out = MarketSnapshot(mid_price=Decimal("110"), spread_bps=1.0, bar_volume=10000.0, bar_volatility=0.0)
    broker.submit(_mk_order(Side.LONG, "1"), snap_in)
    broker.submit(_mk_order(Side.SHORT, "1"), snap_out)
    book = broker.positions[("BTC-PERP", Venue.KRAKEN_FUTURES)]
    assert book.realized_pnl > 0


def test_nav_with_marks(broker, snap):
    broker.submit(_mk_order(Side.LONG, "1"), snap)
    nav = broker.nav({("BTC-PERP", Venue.KRAKEN_FUTURES): Decimal("105")})
    # Position worth 105, cash ~895 minus slippage+fee
    assert nav > Decimal("995") and nav < Decimal("1005")


def test_slippage_is_positive_against_us(broker, snap):
    order = _mk_order(Side.LONG, "10")  # bigger order -> more impact
    fill = broker.submit(order, snap)
    assert fill.price > snap.mid_price  # long pays up
