"""Strategy interface.

A strategy is a deterministic function from (market state, portfolio state)
to a list of Signals. It owns its feature pipeline and its model. It does NOT
own sizing, risk, or execution — those are downstream and not bypassable.

A new strategy MUST:
  1. Subclass Strategy.
  2. Implement `prepare()` for offline training/loading.
  3. Implement `evaluate()` returning a (possibly empty) list of Signals.
  4. Provide a feature manifest (list of feature names + lineage).
  5. Pass a backtest gate: walk-forward Sharpe > 1.0 net of costs, max DD < 15%,
     ≥ 200 OOS trades, Deflated Sharpe > 0.95 confidence. (See BUILD_PLAN.md
     Phase 2 exit criterion.)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from helios.types import PortfolioState, Signal, StrategyId


@dataclass(frozen=True, slots=True)
class StrategyContext:
    """Read-only context handed to a strategy at each tick.

    `as_of` is the canonical "now" — the strategy may only query data with
    `available_at <= as_of`. The data plane's PIT guard enforces this; the
    strategy must not bypass it.
    """
    as_of: datetime
    portfolio: PortfolioState
    universe: tuple[str, ...]  # symbols this strategy is allowed to consider


class Strategy(ABC):
    id: StrategyId
    feature_manifest: tuple[str, ...] = field(default=())

    @abstractmethod
    async def prepare(self) -> None:
        """Load model artifact, warm any caches. Called once at boot."""
        ...

    @abstractmethod
    async def evaluate(self, ctx: StrategyContext) -> list[Signal]:
        """Return zero or more Signals. MUST be deterministic given inputs +
        loaded model. MUST NOT have side effects beyond logging."""
        ...

    def __init_subclass__(cls, **kw: object) -> None:
        super().__init_subclass__(**kw)
        if not hasattr(cls, "id"):
            raise TypeError(f"{cls.__name__} must declare class attr `id: StrategyId`")
