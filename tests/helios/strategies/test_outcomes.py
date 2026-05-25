"""Tests for outcome metrics + exit-policy simulators."""
from __future__ import annotations

import pytest

from helios.strategies.a2_meme_snipe.outcomes import (
    Candle,
    apply_slippage,
    compute_outcome,
    policy_buy_and_hold,
    policy_fixed_target_stop,
    policy_trailing_stop,
)


def _c(t: int, o: float, h: float, l: float, c: float, v: float = 0.0) -> Candle:
    return Candle(unix_time=t, o=o, h=h, l=l, c=c, v=v)


def test_compute_outcome_pumps_then_dumps():
    # Entry at 1.0, peaks at 3.0 (3x), dumps to 0.6, ends at 0.8
    candles = [
        _c(1000, 1.0, 1.2, 0.9, 1.1),
        _c(1060, 1.1, 2.5, 1.0, 2.2),    # crosses 2x
        _c(1120, 2.2, 3.0, 2.0, 2.5),    # peak
        _c(1180, 2.5, 2.5, 0.6, 0.8),    # dump
    ]
    out = compute_outcome(candles, entry_unix=1000, entry_price=1.0)
    assert out is not None
    assert out.max_pump_pct == pytest.approx(2.0)  # 3.0 / 1.0 - 1
    assert out.max_dump_pct == pytest.approx(0.4)  # 1 - 0.6/1.0
    assert out.final_pct == pytest.approx(-0.2)
    assert out.hit_2x and not out.hit_5x
    assert out.time_to_2x_sec == 60  # second bar


def test_compute_outcome_entry_in_middle_of_window():
    candles = [
        _c(0, 0.5, 0.6, 0.4, 0.5),  # before entry — ignored
        _c(60, 1.0, 1.1, 0.9, 1.05),
        _c(120, 1.05, 2.5, 1.0, 2.2),
    ]
    out = compute_outcome(candles, entry_unix=60, entry_price=1.0)
    assert out is not None
    assert out.n_candles == 2
    assert out.hit_2x


def test_compute_outcome_no_window():
    candles = [_c(0, 1.0, 1.1, 0.9, 1.0)]
    out = compute_outcome(candles, entry_unix=1000, entry_price=1.0)
    assert out is None


def test_compute_outcome_zero_entry_returns_none():
    candles = [_c(0, 1.0, 1.0, 1.0, 1.0)]
    assert compute_outcome(candles, entry_unix=0, entry_price=0.0) is None


def test_policy_fixed_target_hit():
    # Target 3x at entry=1.0 => 3.0
    candles = [
        _c(0, 1.0, 1.5, 0.95, 1.4),
        _c(60, 1.4, 3.1, 1.3, 2.9),  # hits 3x
    ]
    r = policy_fixed_target_stop(candles, 0, 1.0, target_mult=3.0, stop_pct=0.5)
    assert r == pytest.approx(2.0)


def test_policy_fixed_stop_hit():
    candles = [
        _c(0, 1.0, 1.1, 0.4, 0.45),  # low 0.4 < stop 0.5
    ]
    r = policy_fixed_target_stop(candles, 0, 1.0, target_mult=3.0, stop_pct=0.5)
    assert r == pytest.approx(-0.5)


def test_policy_fixed_stop_wins_when_both_hit_same_bar():
    """Conservative tie-break: assume stop fires first (safer assumption)."""
    candles = [
        _c(0, 1.0, 3.5, 0.4, 1.5),  # both target and stop in same bar
    ]
    r = policy_fixed_target_stop(candles, 0, 1.0, target_mult=3.0, stop_pct=0.5)
    assert r == pytest.approx(-0.5)


def test_policy_trailing_stop():
    # Steady rise; each bar's low stays above 50%-from-peak so we never trigger,
    # ending with full final_close return. Peak walks up monotonically.
    candles = [
        _c(0, 1.0, 2.0, 1.5, 1.8),    # peak=2.0, trigger=1.0, low=1.5 > 1.0 — hold
        _c(60, 1.8, 5.0, 3.0, 4.5),   # peak=5.0, trigger=2.5, low=3.0 > 2.5 — hold
        _c(120, 4.5, 4.6, 3.5, 4.0),  # peak=5.0, trigger=2.5, low=3.5 > 2.5 — hold
    ]
    # No trailing stop fired => returns final close (4.0) vs entry (1.0) = 3.0
    r = policy_trailing_stop(candles, 0, 1.0, trail_pct=0.5)
    assert r == pytest.approx(3.0)


def test_policy_trailing_stop_fires_on_drawdown():
    """When a later bar's low drops below the trail trigger, exit there."""
    candles = [
        _c(0, 1.0, 2.0, 1.5, 1.8),    # peak=2.0, trigger=1.0, hold
        _c(60, 1.8, 5.0, 3.0, 4.5),   # peak=5.0, trigger=2.5, hold
        _c(120, 4.5, 4.6, 2.0, 2.1),  # low=2.0 < trigger 2.5 — exit at 2.5
    ]
    r = policy_trailing_stop(candles, 0, 1.0, trail_pct=0.5)
    # Exit at trail_trigger (2.5) / entry (1.0) - 1 = 1.5
    assert r == pytest.approx(1.5)


def test_policy_buy_and_hold_equals_final_pct():
    candles = [
        _c(0, 1.0, 1.5, 0.95, 1.4),
        _c(60, 1.4, 2.0, 1.3, 1.7),
    ]
    o = compute_outcome(candles, 0, 1.0)
    assert policy_buy_and_hold(o) == pytest.approx(0.7)


def test_apply_slippage_breaks_even_at_zero_raw():
    """0% raw return with 10% slippage each leg => realized ~ -18.2%."""
    realized = apply_slippage(0.0, 0.10)
    assert realized == pytest.approx((0.9 / 1.1) - 1.0, abs=1e-6)


def test_apply_slippage_compresses_winners():
    """A 100% raw winner after 10%/10% slippage."""
    realized = apply_slippage(1.0, 0.10)
    # (0.9 / 1.1) * 2 - 1
    assert realized == pytest.approx((0.9 / 1.1) * 2.0 - 1.0, abs=1e-6)


def test_apply_slippage_zero_slippage_is_identity():
    assert apply_slippage(0.5, 0.0) == pytest.approx(0.5)
