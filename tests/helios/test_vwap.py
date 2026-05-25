"""Tests for VWAP slicer."""
from __future__ import annotations

from decimal import Decimal

import pytest

from helios.execution.vwap import vwap_schedule


def test_total_quantity_preserved():
    sched = vwap_schedule(Decimal("100"), n_slices=5, volume_profile=[1, 2, 3, 2, 1])
    assert sum(s.qty for s in sched) == Decimal("100")


def test_weighted_distribution():
    sched = vwap_schedule(Decimal("90"), n_slices=3, volume_profile=[1, 2, 3])
    # Weights normalize to 1/6, 2/6, 3/6 -> 15, 30, 45 (float->Decimal rounding tolerated)
    assert abs(sched[0].qty - Decimal("15")) < Decimal("0.001")
    assert abs(sched[1].qty - Decimal("30")) < Decimal("0.001")
    # Last slice eats residue to preserve total exactly
    assert sum(s.qty for s in sched) == Decimal("90")


def test_uniform_fallback_on_zero_profile():
    sched = vwap_schedule(Decimal("100"), n_slices=4, volume_profile=[0, 0, 0, 0])
    # Last slice eats rounding residue; total preserved
    assert sum(s.qty for s in sched) == Decimal("100")


def test_invalid_profile_length():
    with pytest.raises(ValueError):
        vwap_schedule(Decimal("100"), n_slices=3, volume_profile=[1, 2])


def test_delays_monotonic():
    sched = vwap_schedule(Decimal("100"), n_slices=5, volume_profile=[1] * 5, spread_seconds=10)
    for i in range(1, len(sched)):
        assert sched[i].delay_seconds > sched[i - 1].delay_seconds
