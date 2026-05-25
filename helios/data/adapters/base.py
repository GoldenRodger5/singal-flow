"""Adapter base classes. Every concrete adapter (Kraken, Coinbase, Solana, etc.)
implements these so strategies can stay venue-agnostic.

Note: all bars/ticks carry both `event_time` (exchange clock) and `available_at`
(our clock when we received the message). Strategies and the backtest engine
both key off `available_at` to prevent lookahead bias.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from helios.types import Fill, Order, Position, Venue


class VenueError(RuntimeError):
    """Wraps any venue-side failure (auth, rate-limit, network, exchange error)."""


@dataclass(frozen=True, slots=True)
class Bar:
    symbol: str
    venue: Venue
    interval: str  # "1m", "5m", "1h", ...
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    event_time: datetime
    available_at: datetime


@dataclass(frozen=True, slots=True)
class Tick:
    symbol: str
    venue: Venue
    bid: Decimal
    ask: Decimal
    last: Decimal
    bid_size: Decimal
    ask_size: Decimal
    event_time: datetime
    available_at: datetime


class MarketDataSource(ABC):
    @abstractmethod
    async def fetch_bars(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> list[Bar]: ...

    @abstractmethod
    async def stream_bars(self, symbol: str, interval: str):  # type: ignore[no-untyped-def]
        """Async generator of Bar objects. Concrete impls yield."""
        ...

    @abstractmethod
    async def stream_ticks(self, symbol: str):  # type: ignore[no-untyped-def]
        ...


class ExecutionVenue(ABC):
    @abstractmethod
    async def submit(self, order: Order) -> Fill: ...

    @abstractmethod
    async def cancel(self, client_order_id: str) -> None: ...

    @abstractmethod
    async def positions(self) -> list[Position]: ...

    @abstractmethod
    async def balance_usd(self) -> Decimal: ...
