"""Vector memory of past observations + outcomes.

When the bot encounters a new setup, it queries "have I seen something like
this before, and what happened?". Output of the query feeds straight into
the decision: if 200 similar setups historically averaged +2R, take the trade.
If they averaged -0.8R, skip it.

This is the "pattern memory" layer of REVOLUTION_PLAN.md §11. Without it the
self-learning loop has nothing to learn from. With it, every closed trade
adds to the bot's empirical experience and improves future decisions.
"""
from helios.memory.vector_store import (
    PatternQuery,
    PatternRecord,
    VectorMemory,
)

__all__ = ["PatternQuery", "PatternRecord", "VectorMemory"]
