"""Simple allocator: Signal -> Intent via fractional Kelly. Phase 1."""
from __future__ import annotations

from decimal import Decimal

from helios.sizing import KellyParams, fractional_kelly
from helios.types import Intent, PortfolioState, Side, Signal


def simple_allocate(
    signal: Signal,
    state: PortfolioState,
    win_prob: float,
    win_loss_ratio: float,
    leverage: float,
    kelly_fraction: float = 0.25,
) -> Intent | None:
    """Return an Intent sized off the signal's conformal lower bound, or None
    if the sizer says don't trade.
    """
    params = KellyParams(
        win_prob=win_prob,
        win_loss_ratio=win_loss_ratio,
        conformal_lower=signal.confidence_lower,
        kelly_fraction=kelly_fraction,
    )
    notional = fractional_kelly(state.nav_usd, params)
    if notional == 0:
        return None

    side = Side.LONG if signal.direction == 1 else Side.SHORT
    if signal.target_price is None:
        raise ValueError(f"Signal must include target_price; strategy={signal.strategy.value}")

    return Intent(
        strategy=signal.strategy,
        symbol=signal.symbol,
        venue=signal.venue,
        side=side,
        notional_usd=notional,
        leverage=leverage,
        stop_price=signal.invalidation_price,
        take_profit_price=signal.target_price,
        signal_ref=signal,
    )
