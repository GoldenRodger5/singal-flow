"""Allocator — translates per-strategy Signals into Intents with sized notionals.

ContextualBandit (Thompson-sampling Beta-Bernoulli over Signal.confidence_bin
per regime) is the long-term allocator. For Phase 1 the simple sizer just
applies fractional Kelly off the conformal lower bound.
"""
from helios.allocator.bandit import StrategyBandit
from helios.allocator.simple import simple_allocate

__all__ = ["StrategyBandit", "simple_allocate"]
