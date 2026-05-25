"""Execution layer.

Phase-1 components:
  PaperBroker      — deterministic in-process broker for backtests and paper trading
  Router           — routes Orders to the right venue (paper or live)
  vwap.py          — deterministic VWAP slicer baseline (RL replaces this in Phase 4)

Live broker adapters (KrakenFutures, CoinbaseAdvanced, ...) implement the
ExecutionVenue ABC in helios.data.adapters.base.
"""
from helios.execution.paper_broker import PaperBroker
from helios.execution.router import ExecutionRouter
from helios.execution.vwap import vwap_schedule

__all__ = ["ExecutionRouter", "PaperBroker", "vwap_schedule"]
