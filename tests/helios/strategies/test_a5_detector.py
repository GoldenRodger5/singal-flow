"""Tests for the A5 sentiment-velocity detector."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from helios.strategies.a5_sentiment.detector import (
    MentionEvent,
    SentimentDetector,
)


def _mention(ticker: str, secs_ago: int, source: str = "x", weight: float = 1.0,
             now: datetime | None = None) -> MentionEvent:
    now = now or datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    return MentionEvent(
        ticker=ticker, source=source,
        timestamp=now - timedelta(seconds=secs_ago),
        weight=weight,
    )


def test_no_mentions_no_signal():
    d = SentimentDetector()
    assert d.evaluate("WIF") is None


def test_low_baseline_filters_out():
    d = SentimentDetector(min_baseline_mentions=10.0)
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Only 3 mentions ever — below baseline threshold
    for sec in (30, 50, 55):
        d.ingest_mention(_mention("WIF", sec, now=now))
    assert d.evaluate("WIF", now=now) is None


def test_z_score_threshold_must_be_exceeded():
    """High z-threshold + small spike → no signal."""
    d = SentimentDetector(z_score_threshold=20.0, min_baseline_mentions=5.0)
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Baseline: 1 mention/min for 30 min, well clear of signal-window boundary
    for i in range(30):
        d.ingest_mention(_mention("BTC", 120 + i * 60, now=now))
    d.ingest_mention(_mention("BTC", 30, now=now))
    d.ingest_mention(_mention("BTC", 10, now=now))
    sig = d.evaluate("BTC", now=now)
    # Threshold 20σ — way too strict to fire on 2 mentions
    assert sig is None


def test_strong_velocity_spike_emits_signal():
    d = SentimentDetector(
        z_score_threshold=3.0,
        min_baseline_mentions=10.0,
        signal_cooldown_seconds=0,
    )
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Baseline: ~1/min over 60 min
    for i in range(60):
        d.ingest_mention(_mention("WIF", 70 + i * 60, now=now))
    # Sudden spike: 30 mentions in the last 60 seconds
    for _ in range(30):
        d.ingest_mention(_mention("WIF", 30, now=now))
    sig = d.evaluate("WIF", now=now)
    assert sig is not None
    assert sig.z_score > 3.0
    assert sig.mentions_last_minute >= 30  # rate is per-min


def test_cooldown_suppresses_followup_signals():
    d = SentimentDetector(
        z_score_threshold=3.0,
        min_baseline_mentions=5.0,
        signal_cooldown_seconds=600,
    )
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(60):
        d.ingest_mention(_mention("WIF", 70 + i * 60, now=now))
    for _ in range(30):
        d.ingest_mention(_mention("WIF", 30, now=now))
    sig1 = d.evaluate("WIF", now=now)
    assert sig1 is not None
    # Re-evaluate 5 min later → still cooldown
    later = now + timedelta(minutes=5)
    for _ in range(20):
        d.ingest_mention(_mention("WIF", 10, now=later))
    sig2 = d.evaluate("WIF", now=later)
    assert sig2 is None


def test_correlation_gate_suppresses_signal_when_price_already_moved():
    d = SentimentDetector(z_score_threshold=3.0, min_baseline_mentions=5.0)
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    # Baseline mentions
    for i in range(60):
        d.ingest_mention(_mention("WIF", 70 + i * 60, now=now))
    # Spike
    for _ in range(30):
        d.ingest_mention(_mention("WIF", 30, now=now))
    # Add correlated price data: prices rose with mentions in the last 10 min
    # 10 buckets, mentions vs price perfectly correlated
    for i in range(10):
        ts = now - timedelta(minutes=10 - i)
        # Inject extra mentions in increasing rate
        for _ in range(i + 1):
            d.ingest_mention(_mention("WIF", int((now - ts).total_seconds() - 10), now=now))
        d.ingest_price("WIF", price=100.0 + i * 2.0, ts=ts)
    sig = d.evaluate("WIF", now=now)
    # Strong correlation should kill the signal
    assert sig is None


def test_signal_includes_source_breakdown():
    d = SentimentDetector(z_score_threshold=3.0, min_baseline_mentions=5.0, signal_cooldown_seconds=0)
    now = datetime(2026, 5, 25, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(60):
        d.ingest_mention(_mention("PEPE", 70 + i * 60, now=now))
    # Mixed sources in the signal window
    for _ in range(15):
        d.ingest_mention(_mention("PEPE", 30, source="x", now=now))
    for _ in range(15):
        d.ingest_mention(_mention("PEPE", 20, source="farcaster", now=now))
    sig = d.evaluate("PEPE", now=now)
    assert sig is not None
    assert "x" in sig.contributing_sources
    assert "farcaster" in sig.contributing_sources
