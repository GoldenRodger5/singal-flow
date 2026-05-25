"""Tests for tearsheet metrics."""
from __future__ import annotations

import numpy as np
import pytest

from helios.backtest.tearsheet import (
    deflated_sharpe,
    hit_rate,
    max_drawdown,
    sharpe,
    sortino,
    tearsheet,
    win_loss_ratio,
)


def test_sharpe_zero_returns():
    assert sharpe(np.zeros(100)) == 0.0


def test_sharpe_positive_returns():
    np.random.seed(0)
    r = np.random.normal(0.001, 0.01, 252)
    sr = sharpe(r, periods_per_year=252)
    assert sr > 0


def test_sharpe_negative_returns_negative():
    np.random.seed(1)
    r = np.random.normal(-0.001, 0.01, 252)
    assert sharpe(r, periods_per_year=252) < 0


def test_max_drawdown_simple():
    # +10%, -50%, +0%, -50% sequence => peak after first, deep trough
    returns = np.array([0.1, -0.5, 0.0, -0.5])
    mdd = max_drawdown(returns)
    assert mdd > 0.7


def test_max_drawdown_monotonic_up():
    returns = np.full(100, 0.01)
    assert max_drawdown(returns) == pytest.approx(0.0, abs=1e-9)


def test_hit_rate():
    returns = np.array([0.01, -0.005, 0.02, -0.01, 0.003])
    assert hit_rate(returns) == pytest.approx(0.6)


def test_win_loss_ratio():
    returns = np.array([0.02, -0.01, 0.04, -0.02])
    # avg win = 0.03, avg loss = 0.015, ratio = 2.0
    assert win_loss_ratio(returns) == pytest.approx(2.0)


def test_sortino_no_downside():
    returns = np.array([0.01, 0.02, 0.005, 0.015])
    so = sortino(returns)
    assert so == float("inf")


def test_deflated_sharpe_penalty_for_many_trials():
    np.random.seed(0)
    r = np.random.normal(0.001, 0.01, 500)
    sr = sharpe(r)
    dsr_1 = deflated_sharpe(sr, r, n_trials=1)
    dsr_100 = deflated_sharpe(sr, r, n_trials=100)
    # More trials => lower confidence the edge is real (DSR shrinks)
    assert dsr_100 <= dsr_1


def test_tearsheet_assembles_correctly():
    np.random.seed(42)
    r = np.random.normal(0.0005, 0.01, 252)
    ts = tearsheet(r, periods_per_year=252, n_trials=10)
    assert ts.n_periods == 252
    assert ts.deflated_sharpe is not None
    assert 0.0 <= ts.hit_rate <= 1.0
    assert ts.max_drawdown >= 0.0
