"""Tests for the A3 liquidation cascade detector. Pure-logic tests."""
from __future__ import annotations

import pytest

from helios.strategies.a3_liq_hunt.detector import (
    LiquidationCluster,
    LiquidationDetector,
)


@pytest.fixture
def det() -> LiquidationDetector:
    return LiquidationDetector(
        min_cluster_size_usd=100_000,
        max_cluster_distance_pct=0.05,
        cascade_min_magnitude_pct=0.02,
    )


# ---------- detect_clusters ----------

def test_no_buckets_returns_empty(det):
    assert det.detect_clusters("BTC", 50000.0, []) == []


def test_zero_price_returns_empty(det):
    assert det.detect_clusters("BTC", 0.0, [(50000.0, 1_000_000)]) == []


def test_filters_below_min_size(det):
    buckets = [(49500.0, 50_000), (50500.0, 200_000)]
    out = det.detect_clusters("BTC", 50000.0, buckets)
    assert len(out) == 1
    assert out[0].estimated_size_usd == 200_000


def test_filters_too_far_clusters(det):
    # 5% threshold, so 60000 is 20% away — too far
    buckets = [(50500.0, 1_000_000), (60000.0, 5_000_000)]
    out = det.detect_clusters("BTC", 50000.0, buckets)
    assert len(out) == 1
    assert out[0].price_level == 50500.0


def test_long_vs_short_classification(det):
    # Below current = longs liquidated when price drops; above = shorts squeezed up
    buckets = [(49500.0, 500_000), (50500.0, 800_000)]
    out = det.detect_clusters("BTC", 50000.0, buckets)
    sides = {c.price_level: c.side for c in out}
    assert sides[49500.0] == "long"
    assert sides[50500.0] == "short"


def test_density_sorted_desc(det):
    buckets = [(49800.0, 200_000), (50100.0, 800_000), (50400.0, 500_000)]
    out = det.detect_clusters("BTC", 50000.0, buckets)
    # All within range, sorted by density desc
    assert out[0].estimated_size_usd == 800_000
    assert out[-1].estimated_size_usd == 200_000


# ---------- detect_recent_cascade ----------

def test_insufficient_ohlc_returns_none(det):
    ohlc = [{"time": 0, "o": 100, "h": 101, "l": 99, "c": 100, "v": 1}]
    assert det.detect_recent_cascade("BTC", ohlc, []) is None


def test_small_move_not_cascade(det):
    # 0.5% range — below the 2% threshold
    ohlc = [
        {"time": 0,   "o": 100.0, "h": 100.2, "l": 99.8, "c": 100.1, "v": 1},
        {"time": 60,  "o": 100.1, "h": 100.3, "l": 99.9, "c": 100.0, "v": 1},
        {"time": 120, "o": 100.0, "h": 100.5, "l": 99.7, "c": 100.4, "v": 1},
        {"time": 180, "o": 100.4, "h": 100.5, "l": 100.0, "c": 100.2, "v": 1},
        {"time": 240, "o": 100.2, "h": 100.4, "l": 100.0, "c": 100.1, "v": 1},
    ]
    assert det.detect_recent_cascade("BTC", ohlc, []) is None


def test_real_cascade_detected(det):
    # 5% drop in 5 minutes — qualifying cascade
    ohlc = [
        {"time": 0,   "o": 100.0, "h": 100.5, "l": 99.5, "c": 100.0, "v": 1},
        {"time": 60,  "o": 100.0, "h": 100.5, "l": 98.0, "c": 98.5, "v": 1},
        {"time": 120, "o": 98.5,  "h": 99.0,  "l": 96.5, "c": 96.8, "v": 1},
        {"time": 180, "o": 96.8,  "h": 97.0,  "l": 95.0, "c": 95.3, "v": 1},
        {"time": 240, "o": 95.3,  "h": 96.0,  "l": 94.8, "c": 95.5, "v": 1},
    ]
    liqs = [(60, 500_000), (120, 1_500_000), (180, 2_000_000)]
    ev = det.detect_recent_cascade("BTC", ohlc, liqs)
    assert ev is not None
    assert ev.direction == "down"
    assert ev.magnitude_pct > 0.04
    assert ev.total_liquidations_usd == 4_000_000


def test_cascade_duration_too_long(det):
    # 60-minute window — exceeds 30-min cascade window default
    ohlc = [
        {"time": 0,    "o": 100.0, "h": 100.5, "l": 99.5, "c": 100.0, "v": 1},
        {"time": 3600, "o": 100.0, "h": 100.5, "l": 95.0, "c": 95.5, "v": 1},
        {"time": 3660, "o": 95.5,  "h": 96.0,  "l": 94.0, "c": 94.5, "v": 1},
        {"time": 3720, "o": 94.5,  "h": 95.0,  "l": 93.5, "c": 94.0, "v": 1},
        {"time": 3780, "o": 94.0,  "h": 94.5,  "l": 93.0, "c": 93.5, "v": 1},
    ]
    assert det.detect_recent_cascade("BTC", ohlc, []) is None


# ---------- score_signal ----------

def test_no_clusters_no_signal(det):
    assert det.score_signal(50000.0, [], None) is None


def test_ride_signal_when_cluster_very_close_and_dense(det):
    # Cluster 1% below current (longs about to be liquidated) and dense
    cluster = LiquidationCluster(
        symbol="BTC", side="long", price_level=49500.0,
        estimated_size_usd=5_000_000, distance_from_current_pct=0.01,
        leverage_density_score=0.8,
    )
    sig = det.score_signal(50000.0, [cluster], None)
    assert sig is not None
    assert sig.variant == "ride"
    assert sig.direction == -1  # push toward longs' liq → price moves down


def test_fade_signal_after_cascade(det):
    from helios.strategies.a3_liq_hunt.detector import LiquidationEvent
    from datetime import datetime, timezone

    cluster = LiquidationCluster(
        symbol="BTC", side="long", price_level=49000.0,
        estimated_size_usd=8_000_000, distance_from_current_pct=0.02,
        leverage_density_score=0.9,
    )
    cascade = LiquidationEvent(
        symbol="BTC", direction="down", magnitude_pct=0.05,
        duration_seconds=600, total_liquidations_usd=12_000_000,
        pre_cascade_price=51500.0, post_cascade_price=48900.0,
        observed_at=datetime.now(timezone.utc),
    )
    sig = det.score_signal(49000.0, [cluster], cascade)
    assert sig is not None
    assert sig.variant == "fade"
    assert sig.direction == +1  # cascade was down, fade is up


def test_no_signal_when_cluster_too_far_and_no_cascade(det):
    cluster = LiquidationCluster(
        symbol="BTC", side="long", price_level=48000.0,
        estimated_size_usd=2_000_000, distance_from_current_pct=0.04,
        leverage_density_score=0.6,
    )
    # 4% away → outside the 1.5% "ride" trigger
    sig = det.score_signal(50000.0, [cluster], None)
    assert sig is None
