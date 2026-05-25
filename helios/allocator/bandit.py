"""StrategyBandit — Thompson sampling over per-strategy Beta-Bernoulli posteriors.

Each strategy gets a (alpha, beta) Beta posterior on its "this trade pays off"
probability, optionally conditioned on a discrete regime.

On every closed trade outcome, the posterior is updated:
    win  -> alpha += 1
    loss -> beta  += 1

When the allocator needs to choose between competing strategies that all have
positive signals at the same time, it samples once from each posterior and
takes the argmax. This is online learning: strategies with newly-confirmed
edges get more capital; strategies whose edge decays get demoted automatically.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from helios.types import StrategyId


@dataclass
class BetaPosterior:
    alpha: float = 1.0  # prior: uniform Beta(1,1)
    beta: float = 1.0

    def update(self, win: bool) -> None:
        if win:
            self.alpha += 1.0
        else:
            self.beta += 1.0

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(self.alpha, self.beta)

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)


@dataclass
class StrategyBandit:
    """Posteriors keyed by (strategy, regime_label). Pass regime_label="" for
    regime-agnostic operation."""

    posteriors: dict[tuple[StrategyId, str], BetaPosterior] = field(default_factory=dict)
    rng: random.Random = field(default_factory=lambda: random.Random(0))

    def _key(self, strategy: StrategyId, regime: str) -> tuple[StrategyId, str]:
        return (strategy, regime)

    def update(self, strategy: StrategyId, regime: str, win: bool) -> None:
        key = self._key(strategy, regime)
        if key not in self.posteriors:
            self.posteriors[key] = BetaPosterior()
        self.posteriors[key].update(win)

    def sample_weight(self, strategy: StrategyId, regime: str) -> float:
        """Sample a per-strategy weight. The orchestrator multiplies the signal
        magnitude by this when deciding capital fraction."""
        key = self._key(strategy, regime)
        if key not in self.posteriors:
            self.posteriors[key] = BetaPosterior()
        return self.posteriors[key].sample(self.rng)

    def mean_estimate(self, strategy: StrategyId, regime: str) -> float:
        key = self._key(strategy, regime)
        if key not in self.posteriors:
            return 0.5
        return self.posteriors[key].mean
