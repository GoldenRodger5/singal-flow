"""Orchestrator loop. The control flow of Helios.

For each tick:
  1. Fetch a current snapshot of PortfolioState.
  2. For each enabled Strategy, call evaluate(ctx) -> List[Signal].
  3. For each Signal, allocator builds an Intent (sized via Kelly).
  4. risk.apply(intent, state) -> Order | Rejection.
  5. router.submit(order, snap) -> Fill.
  6. Bandit.update on close, log everything.

The loop is structured so it can be driven by:
  - Live data (websocket → on_bar callback)
  - Backtest replay (helios/backtest/engine.py iterates historical bars)
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from helios.allocator import simple_allocate
from helios.allocator.bandit import StrategyBandit
from helios.execution.paper_broker import MarketSnapshot
from helios.execution.router import ExecutionRouter
from helios.ops import get_logger
from helios.risk import RiskConfig, apply as risk_apply
from helios.strategies import Strategy, StrategyContext
from helios.types import (
    Fill,
    Order,
    PortfolioState,
    Rejection,
    Signal,
    StrategyId,
    Venue,
)

log = get_logger(__name__)


@dataclass
class StrategyRuntime:
    """Per-strategy runtime parameters fed to the allocator."""
    win_prob: float = 0.55       # online-updated from bandit posterior
    win_loss_ratio: float = 1.8  # online-updated from closed-trade history
    leverage: float = 3.0


@dataclass
class Orchestrator:
    strategies: list[Strategy]
    router: ExecutionRouter
    risk_config: RiskConfig = field(default_factory=RiskConfig)
    bandit: StrategyBandit = field(default_factory=StrategyBandit)
    runtime: dict[StrategyId, StrategyRuntime] = field(default_factory=dict)
    kill_switch_path: str = field(default_factory=lambda: os.getenv("HELIOS_KILL_SWITCH_PATH", "/tmp/helios.kill"))

    async def prepare(self) -> None:
        for s in self.strategies:
            await s.prepare()
            self.runtime.setdefault(s.id, StrategyRuntime())
        log.info("orchestrator_ready", n_strategies=len(self.strategies))

    def _kill_active(self) -> bool:
        return os.path.exists(self.kill_switch_path)

    async def tick(
        self,
        state: PortfolioState,
        snapshots: dict[tuple[str, Venue], MarketSnapshot],
        universe: tuple[str, ...],
        regime_label: str = "",
    ) -> list[Fill | Rejection]:
        """One pass over all strategies. Returns a list of Fills and Rejections
        for audit / observability."""

        if self._kill_active():
            log.warning("tick_skipped_kill_active")
            return []

        # Hot-reload kill into risk config
        cfg = self.risk_config
        if cfg.kill_switch_active != self._kill_active():
            # RiskConfig is frozen; build a new one with the live kill state
            from dataclasses import replace
            cfg = replace(cfg, kill_switch_active=self._kill_active())

        ctx = StrategyContext(
            as_of=datetime.now(timezone.utc),
            portfolio=state,
            universe=universe,
        )

        outcomes: list[Fill | Rejection] = []
        for strat in self.strategies:
            try:
                signals = await strat.evaluate(ctx)
            except Exception as e:  # noqa: BLE001
                log.exception("strategy_evaluate_failed", strategy=strat.id.value, error=str(e))
                continue

            for sig in signals:
                outcome = await self._handle_signal(sig, state, snapshots, regime_label, cfg)
                if outcome is not None:
                    outcomes.append(outcome)
        return outcomes

    async def _handle_signal(
        self,
        signal: Signal,
        state: PortfolioState,
        snapshots: dict[tuple[str, Venue], MarketSnapshot],
        regime_label: str,
        cfg: RiskConfig,
    ) -> Fill | Rejection | None:
        rt = self.runtime.get(signal.strategy, StrategyRuntime())
        # Bandit weight modulates the conformal lower bound — strategies with
        # recently weak performance get sampled to a lower effective edge.
        bandit_weight = self.bandit.sample_weight(signal.strategy, regime_label)
        scaled_signal = Signal(
            strategy=signal.strategy,
            symbol=signal.symbol,
            venue=signal.venue,
            direction=signal.direction,
            magnitude=signal.magnitude,
            confidence=signal.confidence,
            confidence_lower=signal.confidence_lower * bandit_weight,
            invalidation_price=signal.invalidation_price,
            target_price=signal.target_price,
            features_hash=signal.features_hash,
            created_at=signal.created_at,
        )

        intent = simple_allocate(
            scaled_signal,
            state,
            win_prob=rt.win_prob,
            win_loss_ratio=rt.win_loss_ratio,
            leverage=rt.leverage,
        )
        if intent is None:
            log.debug("signal_sized_to_zero", strategy=signal.strategy.value, symbol=signal.symbol)
            return None

        result = risk_apply(intent, state, cfg)
        if isinstance(result, Rejection):
            log.info(
                "intent_rejected",
                rule=result.rule,
                reason=result.reason,
                strategy=signal.strategy.value,
                symbol=signal.symbol,
            )
            return result

        # result is Order
        order: Order = result
        snap = snapshots.get((order.intent.symbol, order.intent.venue))
        if snap is None:
            log.warning("no_snapshot_for_symbol", symbol=order.intent.symbol)
            return None

        fill = self.router.submit(order, snap)
        return fill

    def on_trade_closed(
        self,
        strategy: StrategyId,
        regime_label: str,
        pnl_usd: Decimal,
    ) -> None:
        """Hook called by the position manager (Phase 2) when a position closes.
        Drives bandit updates and online runtime stats."""
        win = pnl_usd > 0
        self.bandit.update(strategy, regime_label, win)
        # Online runtime stats stub; full Bayesian update arrives with
        # helios.models.online_calibration in the next iteration.
        log.info(
            "trade_closed",
            strategy=strategy.value,
            regime=regime_label,
            pnl_usd=str(pnl_usd),
            win=win,
            bandit_posterior_mean=self.bandit.mean_estimate(strategy, regime_label),
        )
