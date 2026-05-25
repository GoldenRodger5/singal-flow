"""Tests for the slippage model."""
from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from helios.backtest.slippage import SlippageInputs, estimate_slippage_bps


def test_zero_participation_returns_half_spread():
    inp = SlippageInputs(order_size=0.0, adv=1000.0, volatility_pct=0.01, spread_bps=10.0)
    assert estimate_slippage_bps(inp) == pytest.approx(5.0)


def test_full_participation_higher_than_half_spread():
    inp = SlippageInputs(order_size=1000.0, adv=1000.0, volatility_pct=0.01, spread_bps=10.0)
    out = estimate_slippage_bps(inp)
    assert out > 5.0


def test_zero_adv_assumes_worst_case():
    """No volume data -> assume full participation, not zero."""
    inp = SlippageInputs(order_size=100.0, adv=0.0, volatility_pct=0.01, spread_bps=10.0)
    out = estimate_slippage_bps(inp)
    assert out > 5.0  # not just the half-spread


def test_negative_inputs_raise():
    with pytest.raises(ValueError):
        SlippageInputs(order_size=-1.0, adv=100.0, volatility_pct=0.01, spread_bps=10.0)


@settings(max_examples=200, deadline=None)
@given(
    size=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    adv=st.floats(min_value=0.0, max_value=1e9, allow_nan=False, allow_infinity=False),
    vol=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    spread=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
)
def test_property_slippage_non_negative_and_bounded(size, adv, vol, spread):
    inp = SlippageInputs(order_size=size, adv=adv, volatility_pct=vol, spread_bps=spread)
    out = estimate_slippage_bps(inp)
    assert out >= 0.0
    # Sanity ceiling: for any reasonable input, slippage shouldn't blow past 100% (10000 bps)
    assert out <= 1_000_000.0  # absurdly loose, just catching NaN/Inf bugs
