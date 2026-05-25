"""Venue adapters — one module per venue. Every adapter implements the same
two interfaces:

    MarketDataSource   — fetch historical and (later) stream live bars/ticks
    ExecutionVenue     — submit/cancel orders, fetch positions

Phase 1 ships the abstract bases + a sandboxed Kraken adapter. Live wiring
arrives in Phase 2 after auth is provisioned out-of-band.
"""
from helios.data.adapters.base import (
    Bar,
    ExecutionVenue,
    MarketDataSource,
    Tick,
    VenueError,
)

__all__ = ["Bar", "ExecutionVenue", "MarketDataSource", "Tick", "VenueError"]
