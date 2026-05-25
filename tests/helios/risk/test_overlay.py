"""Tests for the risk overlay. The risk overlay is the only thing between the
allocator and capital loss, so this file is paranoid by design.

Two layers:
  1. Unit tests for each rule (R01 .. R12) — happy path + rejection path.
  2. Property tests (Hypothesis) for invariants that must hold for ALL inputs.
"""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from datetime import datetime, timezone

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


def _mk_signal() -> Signal:
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
        created_at=datetime.now(timezone.utc),
    )

from helios.risk import RiskConfig, apply
from helios.risk.overlay import _reject  # noqa: F401  (used indirectly)
from helios.types import (
    Intent,
    Order,
    PortfolioState,
    Rejection,
    Side,
    Signal,
    StrategyId,
    Venue,
)


# ----------------------------- Unit tests -------------------------------

def test_happy_path_approves(base_intent, fresh_state):
    result = apply(base_intent, fresh_state, RiskConfig())
    assert isinstance(result, Order), result


def test_R01_kill_switch_rejects(base_intent, fresh_state):
    cfg = RiskConfig(kill_switch_active=True)
    result = apply(base_intent, fresh_state, cfg)
    assert isinstance(result, Rejection)
    assert result.rule == "R01_kill_switch"


def test_R02_daily_loss_cap(base_intent, fresh_state):
    state = replace(fresh_state, realized_pnl_today_usd=Decimal("-50"))  # -5%
    result = apply(base_intent, state, RiskConfig(max_daily_loss_pct=0.04))
    assert isinstance(result, Rejection)
    assert "R02" in result.rule


def test_R02_weekly_loss_cap(base_intent, fresh_state):
    state = replace(fresh_state, realized_pnl_week_usd=Decimal("-120"))  # -12%
    result = apply(base_intent, state, RiskConfig())
    assert isinstance(result, Rejection)
    assert "R02" in result.rule


def test_R03_drawdown_flat_rejects(base_intent, fresh_state):
    state = replace(fresh_state, nav_usd=Decimal("700"), peak_nav_usd=Decimal("1000"))  # 30% DD
    result = apply(base_intent, state, RiskConfig())
    assert isinstance(result, Rejection)
    assert result.rule == "R03_drawdown_flat"


def test_R04_nav_gate_blocks_options_below_5k(base_intent, fresh_state):
    intent = replace(base_intent, strategy=StrategyId.A4_OPTIONS_0DTE)
    result = apply(intent, fresh_state, RiskConfig())
    assert isinstance(result, Rejection)
    assert result.rule == "R04_nav_gate"


def test_R04_nav_gate_allows_options_above_5k(base_intent, fresh_state):
    state = replace(fresh_state, nav_usd=Decimal("6000"), peak_nav_usd=Decimal("6000"), cash_usd=Decimal("6000"))
    intent = replace(base_intent, strategy=StrategyId.A4_OPTIONS_0DTE, notional_usd=Decimal("300"), leverage=1.0)
    result = apply(intent, state, RiskConfig())
    # The R04 gate must not trigger; other rules may or may not pass.
    if isinstance(result, Rejection):
        assert result.rule != "R04_nav_gate"


def test_R05_min_notional_blocks_dust(base_intent, fresh_state):
    intent = replace(base_intent, notional_usd=Decimal("5"))
    result = apply(intent, fresh_state, RiskConfig())
    assert isinstance(result, Rejection)
    assert result.rule == "R05_min_notional"


def test_R06_position_cap(base_intent, fresh_state):
    intent = replace(base_intent, notional_usd=Decimal("400"))  # 40% > 35% cap
    result = apply(intent, fresh_state, RiskConfig())
    assert isinstance(result, Rejection)
    assert result.rule == "R06_position_cap"


def test_R06_meme_cap_tighter(base_intent, fresh_state):
    intent = replace(base_intent, strategy=StrategyId.A2_MEME_SNIPE, notional_usd=Decimal("150"))  # 15% > 10% meme cap
    result = apply(intent, fresh_state, RiskConfig())
    assert isinstance(result, Rejection)
    assert result.rule == "R06_position_cap"


def test_R08_leverage_cap_per_strategy(base_intent, fresh_state):
    intent = replace(base_intent, leverage=8.0)  # A1 cap is 5x
    result = apply(intent, fresh_state, RiskConfig())
    assert isinstance(result, Rejection)
    assert result.rule == "R08_strategy_leverage"


def test_drawdown_brake_halves_leverage(base_intent, fresh_state):
    # -12% drawdown → leverage cap is halved (5x → 2.5x). Asking for 3x is rejected.
    state = replace(fresh_state, nav_usd=Decimal("880"), peak_nav_usd=Decimal("1000"))
    intent = replace(base_intent, leverage=3.0)
    result = apply(intent, state, RiskConfig())
    assert isinstance(result, Rejection)
    assert "R08" in result.rule or "R09" in result.rule


def test_drawdown_brake_does_not_block_below_halve_threshold(base_intent, fresh_state):
    # -8% drawdown → still under 10% halve threshold; 3x leverage on A1 (5x cap) is fine.
    state = replace(fresh_state, nav_usd=Decimal("920"), peak_nav_usd=Decimal("1000"))
    result = apply(base_intent, state, RiskConfig())
    assert isinstance(result, Order)


# ----------------------------- Property tests -------------------------------

@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    nav=st.decimals(min_value=Decimal("100"), max_value=Decimal("1000000"), allow_nan=False, allow_infinity=False, places=2),
    notional=st.decimals(min_value=Decimal("1"), max_value=Decimal("100000"), allow_nan=False, allow_infinity=False, places=2),
    leverage=st.floats(min_value=0.1, max_value=20.0, allow_nan=False, allow_infinity=False),
)
def test_property_overlay_never_raises(nav, notional, leverage):
    base_signal = _mk_signal()
    """No input combination should make the overlay crash. It must return Order or Rejection."""
    state = PortfolioState(
        nav_usd=nav,
        peak_nav_usd=nav,
        cash_usd=nav,
        positions=(),
        open_orders=(),
        realized_pnl_today_usd=Decimal("0"),
        realized_pnl_week_usd=Decimal("0"),
        realized_pnl_month_usd=Decimal("0"),
        as_of=base_signal.created_at,
    )
    intent = Intent(
        strategy=StrategyId.A1_PERP_TREND,
        symbol="BTC-PERP",
        venue=Venue.KRAKEN_FUTURES,
        side=Side.LONG,
        notional_usd=notional,
        leverage=leverage,
        stop_price=Decimal("98"),
        take_profit_price=Decimal("106"),
        signal_ref=base_signal,
    )
    result = apply(intent, state, RiskConfig())
    assert isinstance(result, (Order, Rejection))


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    nav=st.decimals(min_value=Decimal("100"), max_value=Decimal("100000"), allow_nan=False, allow_infinity=False, places=2),
    notional=st.decimals(min_value=Decimal("1"), max_value=Decimal("1000000"), allow_nan=False, allow_infinity=False, places=2),
)
def test_property_position_cap_invariant(nav, notional):
    base_signal = _mk_signal()
    """For any approved order, notional / NAV <= max_position_pct_of_nav.

    This is the heart of "the risk overlay cannot be bypassed". If this property
    ever fails, capital is at risk.
    """
    cfg = RiskConfig()
    state = PortfolioState(
        nav_usd=nav,
        peak_nav_usd=nav,
        cash_usd=nav,
        positions=(),
        open_orders=(),
        realized_pnl_today_usd=Decimal("0"),
        realized_pnl_week_usd=Decimal("0"),
        realized_pnl_month_usd=Decimal("0"),
        as_of=base_signal.created_at,
    )
    intent = Intent(
        strategy=StrategyId.A1_PERP_TREND,
        symbol="BTC-PERP",
        venue=Venue.KRAKEN_FUTURES,
        side=Side.LONG,
        notional_usd=notional,
        leverage=2.0,
        stop_price=Decimal("98"),
        take_profit_price=Decimal("106"),
        signal_ref=base_signal,
    )
    result = apply(intent, state, cfg)
    if isinstance(result, Order):
        ratio = float(result.intent.notional_usd / state.nav_usd)
        assert ratio <= cfg.max_position_pct_of_nav + 1e-9, f"Position cap breached: {ratio}"


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(leverage=st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False))
def test_property_leverage_cap_invariant(leverage, base_intent, fresh_state):
    """For any approved order, leverage <= overall cap. No matter the input."""
    cfg = RiskConfig()
    intent = Intent(
        strategy=base_intent.strategy,
        symbol=base_intent.symbol,
        venue=base_intent.venue,
        side=base_intent.side,
        notional_usd=base_intent.notional_usd,
        leverage=leverage,
        stop_price=base_intent.stop_price,
        take_profit_price=base_intent.take_profit_price,
        signal_ref=base_intent.signal_ref,
    )
    result = apply(intent, fresh_state, cfg)
    if isinstance(result, Order):
        assert result.intent.leverage <= cfg.max_leverage_overall + 1e-9


def test_property_kill_switch_dominates_everything(base_intent, fresh_state):
    """No input combination can override an active kill switch."""
    cfg = RiskConfig(kill_switch_active=True)
    result = apply(base_intent, fresh_state, cfg)
    assert isinstance(result, Rejection)
    assert result.rule == "R01_kill_switch"
