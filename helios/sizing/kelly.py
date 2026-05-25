"""Fractional Kelly with conformal-lower-bound input.

Why conformal lower bound, not point estimate: a model that predicts +5% with
wide uncertainty should size smaller than one that predicts +5% with tight
uncertainty. Using the lower bound of a calibrated prediction interval gives
us that for free.

Why fractional (0.25× default): full Kelly maximizes log-wealth in expectation
but the path is brutal (frequent 50%+ drawdowns). Quarter-Kelly retains ~94%
of the geometric return at a fraction of the drawdown — standard practice in
size-constrained quant shops.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class KellyParams:
    win_prob: float            # P(win), in (0, 1)
    win_loss_ratio: float      # avg_win / avg_loss, > 0
    conformal_lower: float     # lower bound on expected fractional return per trade; can be negative
    kelly_fraction: float = 0.25  # 0.25× full Kelly

    def __post_init__(self) -> None:
        if not 0.0 < self.win_prob < 1.0:
            raise ValueError(f"win_prob must be in (0,1), got {self.win_prob}")
        if self.win_loss_ratio <= 0:
            raise ValueError(f"win_loss_ratio must be > 0, got {self.win_loss_ratio}")
        if not 0.0 < self.kelly_fraction <= 1.0:
            raise ValueError(f"kelly_fraction must be in (0,1], got {self.kelly_fraction}")


def fractional_kelly(nav_usd: Decimal, params: KellyParams) -> Decimal:
    """Return the notional USD to size this trade at.

    Returns Decimal("0") if Kelly says don't trade (negative edge after conformal
    lower bound). This is the "knowing when not to trade" property — sized off
    the *lower* bound, the bot refuses when its uncertainty swamps its edge.
    """
    if nav_usd <= 0:
        return Decimal("0")

    # If the conformal lower bound on expected return is non-positive, don't trade.
    if params.conformal_lower <= 0:
        return Decimal("0")

    # Kelly formula: f* = p - q/b   where p = win_prob, q = 1-p, b = win_loss_ratio
    p = params.win_prob
    q = 1.0 - p
    b = params.win_loss_ratio
    f_full = p - q / b
    if f_full <= 0:
        return Decimal("0")

    # Apply fractional Kelly + scale by conformal lower bound (max 1.0)
    edge_scale = min(1.0, params.conformal_lower / 0.05)  # full size at 5% expected return floor
    f_used = f_full * params.kelly_fraction * edge_scale

    # Hard ceiling — never more than 35% of NAV in a single trade
    f_used = min(f_used, 0.35)

    return nav_usd * Decimal(str(f_used))
