"""PositionManager — tracks open positions, fires stops/targets, closes trades.

For each tick, given current marks, decide for each open position:
  * mark hit stop or beyond? -> close at stop (slippage applied in broker)
  * mark hit target or beyond? -> close at target
  * else -> hold

On close, computes realized PnL and notifies the orchestrator so the bandit
posterior updates.

Phase 1: long-only, single position per symbol. Pyramiding and partial
scale-outs come with the RL execution agent in Phase 4.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from helios.execution.paper_broker import MarketSnapshot, PaperBroker
from helios.types import (
    Intent,
    Order,
    Side,
    Signal,
    StrategyId,
    Venue,
)


@dataclass
class OpenPosition:
    strategy: StrategyId
    symbol: str
    venue: Venue
    side: Side
    qty: Decimal
    entry_price: Decimal
    stop_price: Decimal
    target_price: Decimal | None
    opened_at: datetime


@dataclass
class PositionManager:
    open_positions: dict[tuple[str, Venue], OpenPosition] = field(default_factory=dict)

    def has_open(self, symbol: str, venue: Venue) -> bool:
        return (symbol, venue) in self.open_positions

    def on_fill_open(self, strategy: StrategyId, symbol: str, venue: Venue, side: Side,
                     qty: Decimal, entry_price: Decimal, stop_price: Decimal,
                     target_price: Decimal | None) -> None:
        self.open_positions[(symbol, venue)] = OpenPosition(
            strategy=strategy, symbol=symbol, venue=venue, side=side,
            qty=qty, entry_price=entry_price, stop_price=stop_price,
            target_price=target_price,
            opened_at=datetime.now(timezone.utc),
        )

    def check_exits(
        self,
        broker: PaperBroker,
        snapshots: dict[tuple[str, Venue], MarketSnapshot],
    ) -> list[tuple[StrategyId, Decimal]]:
        """For each open position, check if mark crosses stop or target. If yes,
        close at the broker (which applies slippage) and yield (strategy, pnl).

        Returns list so the orchestrator can update the bandit.
        """
        closed: list[tuple[StrategyId, Decimal]] = []
        for key, pos in list(self.open_positions.items()):
            snap = snapshots.get(key)
            if snap is None:
                continue
            mark = snap.mid_price

            hit_stop = False
            hit_target = False
            if pos.side == Side.LONG:
                if mark <= pos.stop_price:
                    hit_stop = True
                elif pos.target_price is not None and mark >= pos.target_price:
                    hit_target = True
            else:  # SHORT
                if mark >= pos.stop_price:
                    hit_stop = True
                elif pos.target_price is not None and mark <= pos.target_price:
                    hit_target = True

            if not (hit_stop or hit_target):
                continue

            # Build a closing Order. The Intent is synthesized — sized to flatten.
            close_side = Side.SHORT if pos.side == Side.LONG else Side.LONG
            sig = Signal(
                strategy=pos.strategy, symbol=pos.symbol, venue=pos.venue,
                direction=-1 if pos.side == Side.LONG else 1,
                magnitude=0.0, confidence=1.0, confidence_lower=0.0,
                invalidation_price=pos.entry_price, target_price=pos.target_price,
                features_hash="close", created_at=datetime.now(timezone.utc),
            )
            intent = Intent(
                strategy=pos.strategy, symbol=pos.symbol, venue=pos.venue, side=close_side,
                notional_usd=pos.qty * mark, leverage=1.0,
                stop_price=pos.stop_price, take_profit_price=pos.target_price, signal_ref=sig,
            )
            order = Order(
                intent=intent, qty=pos.qty, order_type="market", limit_price=None,
                client_order_id=f"close-{key[0]}-{datetime.now(timezone.utc).timestamp()}",
                approved_at=datetime.now(timezone.utc),
            )
            close_fill = broker.submit(order, snap)

            # PnL: (exit - entry) * qty for long; (entry - exit) * qty for short
            if pos.side == Side.LONG:
                pnl = (close_fill.price - pos.entry_price) * pos.qty
            else:
                pnl = (pos.entry_price - close_fill.price) * pos.qty
            closed.append((pos.strategy, pnl))
            del self.open_positions[key]
        return closed
