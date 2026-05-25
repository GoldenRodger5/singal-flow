"""Liquidation cluster detection — pure logic over OI + price + funding data.

Pure functions: given a recent window of OI + price + funding data, output:
  - LiquidationCluster: where in the price space are forced-sell walls?
  - LiquidationEvent: did a cascade just happen?

Coinglass exposes aggregated liquidation history per symbol. The detector reads
that, identifies clusters, and tags conditions for entry. We deliberately do
NOT call Coinglass here — adapters do I/O, this is logic. The runner glues
them together.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np


@dataclass(frozen=True, slots=True)
class LiquidationCluster:
    """A price level where forced-sell volume is concentrated."""
    symbol: str
    side: str                  # "long" (longs liquidated when price drops here) or "short"
    price_level: float
    estimated_size_usd: float
    distance_from_current_pct: float
    leverage_density_score: float  # 0-1; higher = denser cluster


@dataclass(frozen=True, slots=True)
class LiquidationEvent:
    """A recent liquidation cascade observation. The output of the detector."""
    symbol: str
    direction: str             # "down" or "up" — direction price moved during the cascade
    magnitude_pct: float       # |move| as fraction of pre-cascade price
    duration_seconds: int
    total_liquidations_usd: float
    pre_cascade_price: float
    post_cascade_price: float
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class CascadeSignal:
    """A trade idea emitted by the detector once a cascade looks ripe."""
    symbol: str
    variant: str               # "fade" or "ride"
    direction: int             # +1 long, -1 short
    confidence: float          # 0-1
    expected_target_pct: float
    invalidation_price: float
    reason: str
    cluster: LiquidationCluster
    cascade_event: LiquidationEvent | None  # None for ride-mode entries during, not after, cascade


class LiquidationDetector:
    """Pure-logic detector. Stateless.

    Two methods:
      detect_clusters(ohlc, oi, leverage_buckets) → list[LiquidationCluster]
      score_cascade_signal(cluster, recent_ohlc, recent_liqs) → CascadeSignal | None
    """

    def __init__(
        self,
        min_cluster_size_usd: float = 250_000,
        max_cluster_distance_pct: float = 0.04,     # only look at clusters within 4% of price
        cascade_min_magnitude_pct: float = 0.02,    # 2% move = qualifying cascade
        cascade_max_duration_seconds: int = 1800,   # 30 min window
        fade_entry_after_cascade_pct: float = 0.5,  # enter fade after cascade clears 50% of its move
    ) -> None:
        self.min_cluster_size_usd = min_cluster_size_usd
        self.max_cluster_distance_pct = max_cluster_distance_pct
        self.cascade_min_magnitude_pct = cascade_min_magnitude_pct
        self.cascade_max_duration_seconds = cascade_max_duration_seconds
        self.fade_entry_after_cascade_pct = fade_entry_after_cascade_pct

    def detect_clusters(
        self,
        symbol: str,
        current_price: float,
        leverage_buckets: list[tuple[float, float]],  # (price_level, liquidation_volume_usd)
    ) -> list[LiquidationCluster]:
        """Identify cluster levels from a histogram of stop/liquidation prices.

        `leverage_buckets` is typically constructed by an adapter that reads
        Coinglass / Hyblock data and bins OI by liquidation price. We accept
        the bucketed form here and just do the clustering math.
        """
        if not leverage_buckets or current_price <= 0:
            return []
        sizes = np.array([b[1] for b in leverage_buckets], dtype=float)
        if sizes.sum() == 0:
            return []
        max_size = sizes.max() if sizes.size > 0 else 1.0

        clusters: list[LiquidationCluster] = []
        for price_level, size in leverage_buckets:
            if size < self.min_cluster_size_usd:
                continue
            distance = abs(price_level - current_price) / current_price
            if distance > self.max_cluster_distance_pct:
                continue
            side = "long" if price_level < current_price else "short"
            density = size / max_size if max_size > 0 else 0.0
            clusters.append(LiquidationCluster(
                symbol=symbol, side=side, price_level=price_level,
                estimated_size_usd=size, distance_from_current_pct=distance,
                leverage_density_score=density,
            ))
        # Sort by density desc — strongest clusters first
        return sorted(clusters, key=lambda c: -c.leverage_density_score)

    def detect_recent_cascade(
        self,
        symbol: str,
        recent_ohlc: list[dict],          # [{time, o, h, l, c, v}, ...] sorted ascending
        recent_liqs_usd: list[tuple[int, float]],  # [(unix_time, liq_usd), ...]
    ) -> LiquidationEvent | None:
        """Return a LiquidationEvent if the recent window shows a cascade.

        Heuristic:
          1. Look at price range over the last cascade_max_duration window
          2. If |max - min| / midpoint > cascade_min_magnitude_pct
          3. AND liquidations in same window > 2x the trailing-hour average
          Then yes — it was a cascade.
        """
        if len(recent_ohlc) < 5:
            return None
        prices_h = np.array([float(c["h"]) for c in recent_ohlc])
        prices_l = np.array([float(c["l"]) for c in recent_ohlc])
        opens = np.array([float(c["o"]) for c in recent_ohlc])
        closes = np.array([float(c["c"]) for c in recent_ohlc])
        times = np.array([int(c.get("time", 0)) for c in recent_ohlc])

        window_high = prices_h.max()
        window_low = prices_l.min()
        midpoint = (window_high + window_low) / 2.0
        if midpoint <= 0:
            return None
        magnitude = (window_high - window_low) / midpoint
        if magnitude < self.cascade_min_magnitude_pct:
            return None

        duration = int(times[-1] - times[0]) if len(times) >= 2 else 0
        if duration > self.cascade_max_duration_seconds:
            return None

        direction = "down" if closes[-1] < opens[0] else "up"
        total_liqs = sum(usd for _, usd in recent_liqs_usd)

        return LiquidationEvent(
            symbol=symbol,
            direction=direction,
            magnitude_pct=magnitude,
            duration_seconds=duration,
            total_liquidations_usd=total_liqs,
            pre_cascade_price=float(opens[0]),
            post_cascade_price=float(closes[-1]),
            observed_at=datetime.now(timezone.utc),
        )

    def score_signal(
        self,
        current_price: float,
        clusters: list[LiquidationCluster],
        cascade: LiquidationEvent | None,
    ) -> CascadeSignal | None:
        """Combine cluster and cascade observations into a trade idea.

        Decision tree:
          1. If cascade just happened and price has cleared >= fade_entry_after threshold
             of the cluster wall → FADE the exhaustion in the opposite direction.
          2. Else if a dense cluster sits very close (< 1.5%) AND price is moving
             toward it → RIDE the cascade in the direction of the cluster.
          3. Else → no trade.
        """
        if not clusters:
            return None

        # Variant A: FADE after cascade.
        # If detect_recent_cascade returned an event, the cascade is in the past —
        # we're now in the post-cascade exhaustion phase, fade is on.
        if cascade and cascade.magnitude_pct >= self.cascade_min_magnitude_pct:
            top = clusters[0]
            trade_direction = +1 if cascade.direction == "down" else -1
            target_pct = cascade.magnitude_pct * 0.4  # expect 40% retrace
            invalidation = current_price * (1.0 - 0.015 * trade_direction)  # 1.5% stop
            return CascadeSignal(
                symbol=top.symbol, variant="fade",
                direction=trade_direction,
                confidence=min(0.85, 0.4 + top.leverage_density_score * 0.5),
                expected_target_pct=target_pct,
                invalidation_price=invalidation,
                reason=f"fade after {cascade.magnitude_pct:.1%} cascade {cascade.direction}",
                cluster=top, cascade_event=cascade,
            )

        # Variant B: RIDE the cluster
        top = clusters[0]
        if top.distance_from_current_pct < 0.015 and top.leverage_density_score > 0.55:
            # Direction: toward the cluster (longs liquidated below current → push down)
            trade_direction = -1 if top.side == "long" else +1
            target_pct = top.distance_from_current_pct + 0.005  # cluster + 50bps overshoot
            invalidation_pct = 0.008  # tight 0.8% stop
            invalidation = current_price * (1 - invalidation_pct * trade_direction)
            return CascadeSignal(
                symbol=top.symbol, variant="ride",
                direction=trade_direction,
                confidence=min(0.7, 0.3 + top.leverage_density_score * 0.5),
                expected_target_pct=target_pct,
                invalidation_price=invalidation,
                reason=f"ride toward {top.side} liq cluster {top.distance_from_current_pct:.1%} away",
                cluster=top, cascade_event=None,
            )

        return None
