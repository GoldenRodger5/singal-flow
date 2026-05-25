"""Core domain types. Pure data, no behavior.

Every type is immutable (`frozen=True`) so that they can be passed between
async tasks and the risk overlay without aliasing bugs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


class Venue(str, Enum):
    KRAKEN_SPOT = "kraken_spot"
    KRAKEN_FUTURES = "kraken_futures"
    COINBASE_SPOT = "coinbase_spot"
    COINBASE_DERIV = "coinbase_deriv"
    CME = "cme"
    ALPACA = "alpaca"
    SOLANA_DEX = "solana_dex"


class StrategyId(str, Enum):
    A1_PERP_TREND = "A1_perp_trend"
    A2_MEME_SNIPE = "A2_meme_snipe"
    A3_LIQ_HUNT = "A3_liq_hunt"
    A5_SENT_VEL = "A5_sentiment_velocity"
    A7_FUNDING_REV = "A7_funding_reversion"
    A8_CASH_CARRY = "A8_cash_and_carry"
    # Deferred until NAV >= $5,000:
    A4_OPTIONS_0DTE = "A4_options_0dte"
    A6_EARNINGS = "A6_earnings"
    A9_VRP_WHEEL = "A9_vrp_wheel"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class Signal:
    """A strategy's pre-risk recommendation. magnitude and confidence both in [0, 1].
    direction: +1 long, -1 short."""
    strategy: StrategyId
    symbol: str
    venue: Venue
    direction: int
    magnitude: float
    confidence: float
    confidence_lower: float  # conformal lower bound on expected return
    invalidation_price: Decimal  # hard stop
    target_price: Decimal | None
    features_hash: str  # for audit / reproducibility
    created_at: datetime

    def __post_init__(self) -> None:
        if self.direction not in (-1, 1):
            raise ValueError(f"direction must be -1 or 1, got {self.direction}")
        if not 0.0 <= self.magnitude <= 1.0:
            raise ValueError(f"magnitude must be in [0,1], got {self.magnitude}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")


@dataclass(frozen=True, slots=True)
class Intent:
    """What the allocator wants to do. Risk overlay either approves -> Order, or rejects."""
    strategy: StrategyId
    symbol: str
    venue: Venue
    side: Side
    notional_usd: Decimal
    leverage: float
    stop_price: Decimal
    take_profit_price: Decimal | None
    signal_ref: Signal


@dataclass(frozen=True, slots=True)
class Order:
    """Risk-approved order, ready for the execution layer."""
    intent: Intent
    qty: Decimal
    order_type: str  # "market" | "limit" | "stop_limit"
    limit_price: Decimal | None
    client_order_id: str
    approved_at: datetime


@dataclass(frozen=True, slots=True)
class Fill:
    order_id: str
    symbol: str
    venue: Venue
    side: Side
    qty: Decimal
    price: Decimal
    fee_usd: Decimal
    slippage_bps: float  # vs. mid at submit
    filled_at: datetime


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    venue: Venue
    side: Side
    qty: Decimal
    avg_entry: Decimal
    unrealized_pnl_usd: Decimal
    realized_pnl_usd: Decimal
    leverage: float
    opened_at: datetime


@dataclass(frozen=True, slots=True)
class PortfolioState:
    """Snapshot of the entire account at a point in time. Consumed by the risk overlay."""
    nav_usd: Decimal
    peak_nav_usd: Decimal  # highest NAV ever reached (for drawdown calc)
    cash_usd: Decimal
    positions: tuple[Position, ...]
    open_orders: tuple[Order, ...]
    realized_pnl_today_usd: Decimal
    realized_pnl_week_usd: Decimal
    realized_pnl_month_usd: Decimal
    as_of: datetime

    @property
    def drawdown_pct(self) -> float:
        if self.peak_nav_usd <= 0:
            return 0.0
        return float((self.peak_nav_usd - self.nav_usd) / self.peak_nav_usd)

    @property
    def daily_pnl_pct(self) -> float:
        if self.nav_usd <= 0:
            return 0.0
        return float(self.realized_pnl_today_usd / self.nav_usd)


@dataclass(frozen=True, slots=True)
class Rejection:
    intent: Intent
    rule: str
    reason: str
    rejected_at: datetime
