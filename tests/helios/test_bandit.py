"""Tests for the Thompson-sampling bandit allocator."""
from __future__ import annotations

import random

from helios.allocator.bandit import StrategyBandit
from helios.types import StrategyId


def test_uniform_prior_starts_at_half():
    bandit = StrategyBandit()
    assert bandit.mean_estimate(StrategyId.A1_PERP_TREND, "") == 0.5


def test_wins_push_posterior_up():
    bandit = StrategyBandit()
    for _ in range(20):
        bandit.update(StrategyId.A1_PERP_TREND, "", win=True)
    assert bandit.mean_estimate(StrategyId.A1_PERP_TREND, "") > 0.85


def test_losses_push_posterior_down():
    bandit = StrategyBandit()
    for _ in range(20):
        bandit.update(StrategyId.A1_PERP_TREND, "", win=False)
    assert bandit.mean_estimate(StrategyId.A1_PERP_TREND, "") < 0.15


def test_regime_isolation():
    """A strategy can be a winner in regime X and a loser in regime Y."""
    bandit = StrategyBandit()
    for _ in range(30):
        bandit.update(StrategyId.A1_PERP_TREND, "trend", win=True)
        bandit.update(StrategyId.A1_PERP_TREND, "chop", win=False)
    assert bandit.mean_estimate(StrategyId.A1_PERP_TREND, "trend") > 0.8
    assert bandit.mean_estimate(StrategyId.A1_PERP_TREND, "chop") < 0.2


def test_sample_weight_in_unit_interval():
    bandit = StrategyBandit(rng=random.Random(1))
    for _ in range(100):
        w = bandit.sample_weight(StrategyId.A1_PERP_TREND, "")
        assert 0.0 <= w <= 1.0
