"""Backtest engine. Pure-Python, event-driven, deterministic.

Three pieces compose:
  slippage.py     — order_size, ADV, volatility → expected slippage in bps
  walkforward.py  — generates train/val splits for honest evaluation
  tearsheet.py    — Sharpe, Sortino, Calmar, max DD, deflated Sharpe

The engine itself (engine.py) arrives once strategies have a stable interface.
"""
