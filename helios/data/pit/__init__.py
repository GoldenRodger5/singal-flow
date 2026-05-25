"""Point-in-time correctness layer.

THE prime directive of the data plane: when asked "what did we know at time T?",
the answer must include only data whose `available_at <= T`.

Backtest lookahead bias is the single most common way quant systems lie to
themselves. This module makes lookahead structurally impossible: every
`as_of_query()` call rewrites the user's SQL to inject the PIT filter on each
referenced dataset view.
"""
from helios.data.pit.guard import PITViolation, as_of_query

__all__ = ["PITViolation", "as_of_query"]
