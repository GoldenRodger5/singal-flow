"""Tests for fractional Kelly sizer."""
from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from helios.sizing import KellyParams, fractional_kelly


def test_negative_conformal_returns_zero():
    """If the model isn't confident the trade has positive EV, don't trade."""
    params = KellyParams(win_prob=0.6, win_loss_ratio=2.0, conformal_lower=-0.01)
    assert fractional_kelly(Decimal("1000"), params) == Decimal("0")


def test_zero_conformal_returns_zero():
    params = KellyParams(win_prob=0.6, win_loss_ratio=2.0, conformal_lower=0.0)
    assert fractional_kelly(Decimal("1000"), params) == Decimal("0")


def test_negative_kelly_returns_zero():
    """win_prob 30%, win_loss_ratio 1.5 → f* = 0.3 - 0.7/1.5 < 0. Don't trade."""
    params = KellyParams(win_prob=0.3, win_loss_ratio=1.5, conformal_lower=0.02)
    assert fractional_kelly(Decimal("1000"), params) == Decimal("0")


def test_positive_edge_sizes_positive():
    params = KellyParams(win_prob=0.6, win_loss_ratio=2.0, conformal_lower=0.05)
    size = fractional_kelly(Decimal("1000"), params)
    assert size > 0
    assert size < Decimal("350")  # hard 35% ceiling


def test_hard_ceiling_at_35pct():
    """Even with absurdly good params, single-trade size never exceeds 35% of NAV."""
    params = KellyParams(
        win_prob=0.95,
        win_loss_ratio=10.0,
        conformal_lower=1.0,  # implausibly high
        kelly_fraction=1.0,
    )
    size = fractional_kelly(Decimal("1000"), params)
    assert size <= Decimal("350.01")


def test_invalid_win_prob_raises():
    with pytest.raises(ValueError):
        KellyParams(win_prob=0.0, win_loss_ratio=2.0, conformal_lower=0.05)
    with pytest.raises(ValueError):
        KellyParams(win_prob=1.0, win_loss_ratio=2.0, conformal_lower=0.05)


def test_invalid_win_loss_raises():
    with pytest.raises(ValueError):
        KellyParams(win_prob=0.6, win_loss_ratio=0.0, conformal_lower=0.05)


@settings(max_examples=300, deadline=None)
@given(
    nav=st.decimals(min_value=Decimal("100"), max_value=Decimal("1000000"), allow_nan=False, allow_infinity=False, places=2),
    p=st.floats(min_value=0.01, max_value=0.99, allow_nan=False, allow_infinity=False),
    b=st.floats(min_value=0.1, max_value=20.0, allow_nan=False, allow_infinity=False),
    cl=st.floats(min_value=-1.0, max_value=2.0, allow_nan=False, allow_infinity=False),
)
def test_property_kelly_invariants(nav, p, b, cl):
    """Properties that must hold for ALL inputs:
       1. Output is never negative.
       2. Output never exceeds 35% of NAV.
       3. Output is zero if conformal lower bound is non-positive.
    """
    params = KellyParams(win_prob=p, win_loss_ratio=b, conformal_lower=cl)
    size = fractional_kelly(nav, params)
    assert size >= Decimal("0"), f"Negative size: {size}"
    assert size <= nav * Decimal("0.35001"), f"Ceiling breached: {size} > 35% of {nav}"
    if cl <= 0:
        assert size == Decimal("0"), "Must not trade when conformal lower bound <= 0"
