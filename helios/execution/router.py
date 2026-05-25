"""ExecutionRouter — routes approved Orders to the right venue.

Phase 1: always paper. Phase 6 promotion to a live venue is a config change,
not a code change. The router is the single chokepoint where "paper vs live"
is decided.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from helios.execution.paper_broker import MarketSnapshot, PaperBroker
from helios.ops import get_logger
from helios.types import Fill, Order, Venue

log = get_logger(__name__)


class ExecutionMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


@dataclass
class ExecutionRouter:
    mode: ExecutionMode
    paper: PaperBroker
    # live_adapters: dict[Venue, ExecutionVenue] = {}  # wired in Phase 6

    def submit(self, order: Order, snap: MarketSnapshot) -> Fill:
        if self.mode == ExecutionMode.PAPER:
            fill = self.paper.submit(order, snap)
            log.info(
                "paper_fill",
                order_id=order.client_order_id,
                symbol=order.intent.symbol,
                venue=order.intent.venue.value,
                side=order.intent.side.value,
                qty=str(order.qty),
                price=str(fill.price),
                slip_bps=fill.slippage_bps,
                strategy=order.intent.strategy.value,
            )
            return fill
        raise NotImplementedError("Live execution arrives in Phase 6 after paper validation gate")
