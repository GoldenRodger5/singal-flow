"""A2 Strategy — wires RugFilter into the Strategy ABC.

Per-shot position size is hard-capped (see config); the risk overlay further
enforces A2's aggregate sleeve cap (10% of NAV in helios/risk/overlay.py).

Phase 2.1: strategy responds to a queue of TokenSnapshots (pushed by a future
detection adapter in Phase 2.2). For each candidate, runs RugFilter; if pass,
emits a Signal with the configured per-shot notional. Otherwise logs the
rejection reasons for shadow-mode analysis.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from helios.ops import get_logger
from helios.strategies.a2_meme_snipe.rug_filter import (
    FilterDecision,
    RugFilter,
    RugFilterConfig,
)
from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot
from helios.strategies.base import Strategy, StrategyContext
from helios.types import Signal, StrategyId, Venue

log = get_logger(__name__)


@dataclass
class A2Config:
    rug_filter: RugFilterConfig = field(default_factory=RugFilterConfig)
    per_shot_notional_usd: Decimal = Decimal("50")
    invalidation_pct: float = 0.50            # exit if down 50% from entry
    target_pct: float = 3.0                   # initial profit target 3x (300% from entry)
    confidence_lower_on_pass: float = 0.10    # conformal lower bound proxy when filter passes


class A2MemeSnipe(Strategy):
    id = StrategyId.A2_MEME_SNIPE
    feature_manifest = ()  # filter is logic, not features; manifest is intentionally empty

    def __init__(self, config: A2Config | None = None) -> None:
        self.config = config or A2Config()
        self._filter = RugFilter(self.config.rug_filter)
        # Async queue of candidate TokenSnapshots, pushed by an external
        # detector. evaluate() drains the queue per tick.
        self._queue: asyncio.Queue[TokenSnapshot] = asyncio.Queue()
        # Token addresses we've already evaluated (don't double-shoot the same launch)
        self._seen: set[str] = set()

    async def prepare(self) -> None:
        log.info("a2_prepared", per_shot_usd=str(self.config.per_shot_notional_usd))

    def submit_candidate(self, snap: TokenSnapshot) -> None:
        """Called by the detection adapter to push a new candidate into the
        strategy's queue."""
        try:
            self._queue.put_nowait(snap)
        except asyncio.QueueFull:  # pragma: no cover - default queue is unbounded
            log.warning("a2_queue_full", mint=snap.mint_address)

    async def evaluate(self, ctx: StrategyContext) -> list[Signal]:
        signals: list[Signal] = []
        # Drain the queue without blocking
        while not self._queue.empty():
            try:
                snap = self._queue.get_nowait()
            except asyncio.QueueEmpty:  # pragma: no cover
                break
            if snap.mint_address in self._seen:
                continue
            self._seen.add(snap.mint_address)
            sig = self._evaluate_one(snap, ctx)
            if sig is not None:
                signals.append(sig)
        return signals

    def _evaluate_one(self, snap: TokenSnapshot, ctx: StrategyContext) -> Signal | None:
        report = self._filter.check(snap)
        if report.decision == FilterDecision.REJECT:
            log.info(
                "a2_filter_reject",
                mint=snap.mint_address, symbol=snap.symbol,
                reasons=report.reasons,
            )
            return None

        # Build a Signal. Entry at last_trade_price, target at +target_pct, stop at -invalidation_pct.
        if snap.last_trade_price_usd <= 0:
            log.warning("a2_filter_pass_but_price_zero", mint=snap.mint_address)
            return None
        entry = snap.last_trade_price_usd
        stop = entry * (Decimal(1) - Decimal(str(self.config.invalidation_pct)))
        target = entry * (Decimal(1) + Decimal(str(self.config.target_pct)))

        log.info(
            "a2_filter_pass",
            mint=snap.mint_address, symbol=snap.symbol,
            entry=str(entry), stop=str(stop), target=str(target),
        )
        return Signal(
            strategy=self.id,
            symbol=snap.mint_address,   # use mint as symbol on Solana
            venue=Venue.SOLANA_DEX,
            direction=1,                 # always long on a snipe
            magnitude=1.0,
            confidence=0.6,              # filter passing is binary; magnitude is the sizing knob
            confidence_lower=self.config.confidence_lower_on_pass,
            invalidation_price=stop,
            target_price=target,
            features_hash=snap.mint_address[:16],
            created_at=ctx.as_of if ctx.as_of else datetime.now(timezone.utc),
        )
