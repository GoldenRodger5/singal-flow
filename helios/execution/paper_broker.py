"""PaperBroker — in-process, deterministic, slippage-modeled.

Used by:
  * Backtests (consuming historical bars)
  * Paper-trading mode (consuming live bars but not touching real money)

Behavior:
  * Market orders fill instantly at (mid +/- modeled slippage)
  * Maintains positions, cash, and a fill log
  * NEVER touches network — so it cannot leak credentials, cannot place real
    orders, and cannot fail because an exchange did

This is the safety floor while we earn the right to live capital.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from helios.backtest.slippage import SlippageInputs, estimate_slippage_bps
from helios.types import Fill, Order, Side, Venue


@dataclass
class _PositionBook:
    qty: Decimal = Decimal("0")
    avg_price: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")


@dataclass
class MarketSnapshot:
    """Current mid + spread + recent volume for a symbol. Provided by the
    orchestrator at fill time (in live) or replayed from bars (in backtest)."""
    mid_price: Decimal
    spread_bps: float
    bar_volume: float  # most-recent-bar volume in base units
    bar_volatility: float  # most-recent-bar return std (decimal, e.g. 0.005)


class PaperBroker:
    def __init__(self, starting_cash: Decimal = Decimal("1000")) -> None:
        self.cash: Decimal = starting_cash
        self.starting_cash: Decimal = starting_cash
        self.positions: dict[tuple[str, Venue], _PositionBook] = defaultdict(_PositionBook)
        self.fills: list[Fill] = []

    def submit(self, order: Order, snap: MarketSnapshot) -> Fill:
        """Simulate a fill. Pure function over (state, order, snap).

        Slippage is added against us: long fills above mid, short fills below.
        """
        slip_bps = estimate_slippage_bps(SlippageInputs(
            order_size=float(order.qty),
            adv=snap.bar_volume,
            volatility_pct=snap.bar_volatility,
            spread_bps=snap.spread_bps,
        ))
        slip_factor = Decimal(str(slip_bps / 10000.0))
        if order.intent.side == Side.LONG:
            fill_price = snap.mid_price * (Decimal("1") + slip_factor)
        else:
            fill_price = snap.mid_price * (Decimal("1") - slip_factor)

        # Fee: conservative 5 bps round-trip on crypto majors (Kraken Futures taker is ~5bps)
        notional = order.qty * fill_price
        fee = notional * Decimal("0.0005")

        # Update book
        key = (order.intent.symbol, order.intent.venue)
        book = self.positions[key]
        if order.intent.side == Side.LONG:
            new_qty = book.qty + order.qty
            if new_qty > 0:
                # weighted-avg entry
                book.avg_price = (book.avg_price * book.qty + fill_price * order.qty) / new_qty if book.qty >= 0 else fill_price
            book.qty = new_qty
            self.cash -= notional + fee
        else:
            new_qty = book.qty - order.qty
            if book.qty > 0:
                # closing long -> realize PnL on closed portion
                closed = min(book.qty, order.qty)
                book.realized_pnl += (fill_price - book.avg_price) * closed
            book.qty = new_qty
            self.cash += notional - fee

        fill = Fill(
            order_id=order.client_order_id,
            symbol=order.intent.symbol,
            venue=order.intent.venue,
            side=order.intent.side,
            qty=order.qty,
            price=fill_price,
            fee_usd=fee,
            slippage_bps=slip_bps,
            filled_at=datetime.now(timezone.utc),
        )
        self.fills.append(fill)
        return fill

    def nav(self, marks: dict[tuple[str, Venue], Decimal]) -> Decimal:
        """NAV = cash + sum(qty * mark) for each position. Marks are passed in
        so the broker is pure (doesn't need to fetch prices)."""
        equity = self.cash
        for key, book in self.positions.items():
            mark = marks.get(key, book.avg_price)
            equity += book.qty * mark
        return equity
