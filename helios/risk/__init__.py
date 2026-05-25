"""Risk overlay — the only thing between the allocator and the broker.

Every function in this package is pure: same inputs → same output, no I/O, no
mutation. This makes the risk layer property-testable and impossible to bypass
by accident.

The `apply()` function is the canonical entry point. It returns either an
`Order` (approved) or a `Rejection` (denied, with the specific rule that
triggered). The orchestrator is required to route every `Intent` through
`apply()` before any execution call.
"""
from helios.risk.overlay import RiskConfig, apply

__all__ = ["RiskConfig", "apply"]
