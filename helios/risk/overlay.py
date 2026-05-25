"""Risk overlay — converts Intent → Order | Rejection. Pure function.

Rules evaluated in order. First failing rule wins (short-circuit). This
ordering is intentional: hard stops (kill switch, drawdown) before soft
limits (per-position cap, leverage cap).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from helios.types import (
    Intent,
    Order,
    PortfolioState,
    Rejection,
    Side,
    StrategyId,
)


@dataclass(frozen=True, slots=True)
class RiskConfig:
    """All risk parameters in one place. Defaults match the $1k US-compliant starter."""

    # Kill switch (hard halts)
    kill_switch_active: bool = False
    max_drawdown_flat_pct: float = 0.25  # full flatten + alert
    max_daily_loss_pct: float = 0.04
    max_weekly_loss_pct: float = 0.10
    max_monthly_loss_pct: float = 0.18

    # Drawdown brake (de-risking thresholds)
    drawdown_halve_pct: float = 0.10  # halve leverage budget at -10%
    drawdown_quarter_pct: float = 0.18  # quarter leverage at -18%

    # Per-position
    max_position_pct_of_nav: float = 0.35  # any one position
    max_position_pct_meme: float = 0.10  # A2 sleeve total cap
    min_notional_usd: Decimal = Decimal("10")  # below this, economics don't work

    # Leverage
    max_leverage_overall: float = 8.0
    max_leverage_per_strategy: dict[StrategyId, float] = field(
        default_factory=lambda: {
            StrategyId.A1_PERP_TREND: 5.0,
            StrategyId.A3_LIQ_HUNT: 3.0,
            StrategyId.A7_FUNDING_REV: 3.0,
            StrategyId.A8_CASH_CARRY: 1.0,
            StrategyId.A5_SENT_VEL: 3.0,
            StrategyId.A2_MEME_SNIPE: 1.0,  # spot only
        }
    )

    # Per-strategy capital allocation (fraction of NAV); enforced as ceiling
    strategy_alloc_max: dict[StrategyId, float] = field(
        default_factory=lambda: {
            StrategyId.A1_PERP_TREND: 0.40,
            StrategyId.A8_CASH_CARRY: 0.30,
            StrategyId.A3_LIQ_HUNT: 0.15,
            StrategyId.A2_MEME_SNIPE: 0.10,
            StrategyId.A5_SENT_VEL: 0.15,
            StrategyId.A7_FUNDING_REV: 0.10,
        }
    )

    # Asymmetry enforcement: reject if stop distance > X% of entry
    max_stop_distance_pct: float = 0.08

    # Aggregate gross + net exposure
    max_gross_exposure_pct_of_nav: float = 2.0  # 2x gross w/ leverage
    max_net_exposure_pct_of_nav: float = 1.5

    # NAV gates: strategies below this NAV are disabled regardless
    nav_gate_options: Decimal = Decimal("5000")  # A4, A6, A9 off below this


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _reject(intent: Intent, rule: str, reason: str) -> Rejection:
    return Rejection(intent=intent, rule=rule, reason=reason, rejected_at=_now())


def _approve(intent: Intent, qty: Decimal) -> Order:
    return Order(
        intent=intent,
        qty=qty,
        order_type="market",  # execution layer may downgrade to limit; risk doesn't care
        limit_price=None,
        client_order_id=str(uuid.uuid4()),
        approved_at=_now(),
    )


def _strategy_exposure(state: PortfolioState, strategy: StrategyId) -> Decimal:
    """Current open notional USD attributable to a strategy.

    Strategies are tagged via the open Intent on each Order; risk overlay reads it back.
    """
    total = Decimal("0")
    for o in state.open_orders:
        if o.intent.strategy == strategy:
            total += o.intent.notional_usd
    return total


def _gross_exposure(state: PortfolioState) -> Decimal:
    total = Decimal("0")
    for p in state.positions:
        total += abs(p.qty * p.avg_entry) * Decimal(str(p.leverage))
    return total


def _net_exposure(state: PortfolioState) -> Decimal:
    total = Decimal("0")
    for p in state.positions:
        signed = p.qty * p.avg_entry * Decimal(str(p.leverage))
        if p.side == Side.SHORT:
            signed = -signed
        total += signed
    return abs(total)


def _stop_distance_pct(intent: Intent) -> float:
    """Distance from invalidation to entry, as fraction of entry price."""
    entry = intent.signal_ref.invalidation_price  # using as proxy reference
    stop = intent.stop_price
    if intent.signal_ref.target_price is None or entry <= 0:
        # Without a clear entry reference, just compare stop to signal invalidation
        if intent.signal_ref.invalidation_price > 0:
            return abs(float((stop - intent.signal_ref.invalidation_price) / intent.signal_ref.invalidation_price))
        return 0.0
    return abs(float((stop - entry) / entry)) if entry > 0 else 0.0


def apply(intent: Intent, state: PortfolioState, config: RiskConfig) -> Order | Rejection:
    """Apply the full risk-overlay ruleset. Return Order or Rejection.

    Rules in priority order:
      R01 kill switch
      R02 daily / weekly / monthly loss caps
      R03 drawdown flat threshold
      R04 NAV gate for deferred strategies
      R05 min notional (economics)
      R06 per-position cap
      R07 per-strategy allocation cap
      R08 per-strategy leverage cap
      R09 overall leverage cap (post drawdown-brake)
      R10 asymmetry / stop distance cap
      R11 aggregate gross exposure
      R12 aggregate net exposure
    """
    # R01
    if config.kill_switch_active:
        return _reject(intent, "R01_kill_switch", "Kill switch is active")

    # R02 — loss caps
    daily_loss_pct = -float(state.realized_pnl_today_usd / state.nav_usd) if state.nav_usd > 0 else 0.0
    weekly_loss_pct = -float(state.realized_pnl_week_usd / state.nav_usd) if state.nav_usd > 0 else 0.0
    monthly_loss_pct = -float(state.realized_pnl_month_usd / state.nav_usd) if state.nav_usd > 0 else 0.0
    if daily_loss_pct >= config.max_daily_loss_pct:
        return _reject(intent, "R02_daily_loss", f"Daily loss {daily_loss_pct:.2%} >= cap {config.max_daily_loss_pct:.2%}")
    if weekly_loss_pct >= config.max_weekly_loss_pct:
        return _reject(intent, "R02_weekly_loss", f"Weekly loss {weekly_loss_pct:.2%} >= cap")
    if monthly_loss_pct >= config.max_monthly_loss_pct:
        return _reject(intent, "R02_monthly_loss", f"Monthly loss {monthly_loss_pct:.2%} >= cap")

    # R03 — drawdown flat threshold
    if state.drawdown_pct >= config.max_drawdown_flat_pct:
        return _reject(intent, "R03_drawdown_flat", f"Drawdown {state.drawdown_pct:.2%} >= flat threshold")

    # R04 — NAV gate
    deferred = {StrategyId.A4_OPTIONS_0DTE, StrategyId.A6_EARNINGS, StrategyId.A9_VRP_WHEEL}
    if intent.strategy in deferred and state.nav_usd < config.nav_gate_options:
        return _reject(
            intent,
            "R04_nav_gate",
            f"Strategy {intent.strategy.value} requires NAV >= ${config.nav_gate_options}; have ${state.nav_usd}",
        )

    # R05 — economics floor
    if intent.notional_usd < config.min_notional_usd:
        return _reject(intent, "R05_min_notional", f"Notional ${intent.notional_usd} below floor ${config.min_notional_usd}")

    # R06 — per-position cap
    nav = state.nav_usd
    if nav <= 0:
        return _reject(intent, "R06_zero_nav", "Account NAV is zero or negative")
    pos_pct = float(intent.notional_usd / nav)
    cap = config.max_position_pct_meme if intent.strategy == StrategyId.A2_MEME_SNIPE else config.max_position_pct_of_nav
    if pos_pct > cap:
        return _reject(intent, "R06_position_cap", f"Position {pos_pct:.2%} > cap {cap:.2%}")

    # R07 — per-strategy allocation cap (existing + this intent)
    strat_cap_pct = config.strategy_alloc_max.get(intent.strategy)
    if strat_cap_pct is not None:
        existing = _strategy_exposure(state, intent.strategy)
        projected = float((existing + intent.notional_usd) / nav)
        if projected > strat_cap_pct:
            return _reject(
                intent,
                "R07_strategy_alloc",
                f"Strategy alloc {projected:.2%} > cap {strat_cap_pct:.2%} (existing ${existing} + new ${intent.notional_usd})",
            )

    # Drawdown brake adjusts the *leverage cap* — does not reject outright
    leverage_cap_multiplier = 1.0
    if state.drawdown_pct >= config.drawdown_quarter_pct:
        leverage_cap_multiplier = 0.25
    elif state.drawdown_pct >= config.drawdown_halve_pct:
        leverage_cap_multiplier = 0.5

    # R08 — per-strategy leverage
    per_strat_lev = config.max_leverage_per_strategy.get(intent.strategy, 1.0) * leverage_cap_multiplier
    if intent.leverage > per_strat_lev:
        return _reject(
            intent,
            "R08_strategy_leverage",
            f"Leverage {intent.leverage}x > strategy cap {per_strat_lev}x (drawdown-adjusted)",
        )

    # R09 — overall leverage cap
    overall_lev_cap = config.max_leverage_overall * leverage_cap_multiplier
    if intent.leverage > overall_lev_cap:
        return _reject(
            intent,
            "R09_overall_leverage",
            f"Leverage {intent.leverage}x > overall cap {overall_lev_cap}x (drawdown-adjusted)",
        )

    # R10 — asymmetry / stop distance
    stop_dist = _stop_distance_pct(intent)
    if stop_dist > config.max_stop_distance_pct:
        return _reject(
            intent,
            "R10_stop_distance",
            f"Stop distance {stop_dist:.2%} > cap {config.max_stop_distance_pct:.2%} — asymmetry violated",
        )

    # R11 — aggregate gross exposure
    projected_gross = _gross_exposure(state) + intent.notional_usd * Decimal(str(intent.leverage))
    gross_pct = float(projected_gross / nav)
    if gross_pct > config.max_gross_exposure_pct_of_nav:
        return _reject(
            intent,
            "R11_gross_exposure",
            f"Gross {gross_pct:.2f}x > cap {config.max_gross_exposure_pct_of_nav:.2f}x",
        )

    # R12 — aggregate net exposure (simplified: assume new intent adds same-sign exposure)
    sign = Decimal("1") if intent.signal_ref.direction == 1 else Decimal("-1")
    projected_net_add = intent.notional_usd * Decimal(str(intent.leverage)) * sign
    projected_net = _net_exposure(state) + abs(projected_net_add)
    net_pct = float(projected_net / nav)
    if net_pct > config.max_net_exposure_pct_of_nav:
        return _reject(
            intent,
            "R12_net_exposure",
            f"Net {net_pct:.2f}x > cap {config.max_net_exposure_pct_of_nav:.2f}x",
        )

    # All rules passed — approve
    qty = intent.notional_usd / intent.signal_ref.invalidation_price if intent.signal_ref.invalidation_price > 0 else Decimal("0")
    return _approve(intent, qty)
