"""Sentiment velocity detector — pure logic.

Given a stream of mention events (each: ticker + timestamp + source + maybe
content), maintain rolling stats and emit signals when mention velocity
accelerates ahead of price.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import mean, pstdev

import numpy as np


@dataclass(frozen=True, slots=True)
class MentionEvent:
    ticker: str            # "$WIF", "BTC", "POPCAT", uppercased + leading-$ stripped
    source: str            # "x", "farcaster", "reddit", "telegram"
    timestamp: datetime
    weight: float = 1.0    # 1.0 for normal account, 0.1 for low-follower accounts, 5.0 for known alpha
    sentiment: float = 0.0 # -1..1 (we don't actually use this for velocity, but log it)


@dataclass(frozen=True, slots=True)
class SentimentSignal:
    ticker: str
    z_score: float
    mentions_last_minute: float    # weighted
    mentions_per_min_baseline: float
    correlation_with_price: float | None  # may be None if no price data
    confidence: float
    suggested_hold_seconds: int
    triggered_at: datetime
    contributing_sources: dict[str, int]


@dataclass
class _TickerState:
    ticker: str
    # Sliding window of (unix_seconds, weight, source) per mention
    mentions: deque = field(default_factory=lambda: deque(maxlen=10_000))
    # Price observations for correlation calc (timestamp, price)
    prices: deque = field(default_factory=lambda: deque(maxlen=600))
    last_signal_unix: float = 0.0  # cooldown


class SentimentDetector:
    """Stateful per-ticker mention-velocity tracker.

    Memory: holds last ~1h of mentions for each ticker we've seen. With ~10k
    cap per ticker, hundreds of tickers, total memory is small (< 50 MB).
    """

    def __init__(
        self,
        baseline_window_seconds: int = 3600,   # 1 hour
        signal_window_seconds: int = 60,       # 1 minute
        z_score_threshold: float = 4.0,        # must be 4 stdev above baseline
        min_baseline_mentions: float = 5.0,    # don't fire on no-baseline tickers
        signal_cooldown_seconds: int = 600,    # 10 min between signals on same ticker
        max_price_correlation: float = 0.5,    # if price already moved with mentions → stale
        suggested_hold_seconds: int = 600,
    ) -> None:
        self.baseline_window = baseline_window_seconds
        self.signal_window = signal_window_seconds
        self.z_threshold = z_score_threshold
        self.min_baseline_mentions = min_baseline_mentions
        self.signal_cooldown = signal_cooldown_seconds
        self.max_price_correlation = max_price_correlation
        self.suggested_hold_seconds = suggested_hold_seconds
        self._tickers: dict[str, _TickerState] = {}

    # ----- Ingestion -----

    def ingest_mention(self, ev: MentionEvent) -> None:
        ticker = ev.ticker.upper().lstrip("$")
        if ticker not in self._tickers:
            self._tickers[ticker] = _TickerState(ticker=ticker)
        state = self._tickers[ticker]
        unix = ev.timestamp.timestamp()
        state.mentions.append((unix, ev.weight, ev.source))
        # Prune mentions older than the baseline window
        cutoff = unix - self.baseline_window
        while state.mentions and state.mentions[0][0] < cutoff:
            state.mentions.popleft()

    def ingest_price(self, ticker: str, price: float, ts: datetime | None = None) -> None:
        """Record a price observation. Used for the correlation gate only.
        Optional — if no prices ingested, correlation check is skipped."""
        ticker = ticker.upper().lstrip("$")
        if ticker not in self._tickers:
            self._tickers[ticker] = _TickerState(ticker=ticker)
        state = self._tickers[ticker]
        ts = ts or datetime.now(timezone.utc)
        unix = ts.timestamp()
        state.prices.append((unix, float(price)))
        cutoff = unix - self.baseline_window
        while state.prices and state.prices[0][0] < cutoff:
            state.prices.popleft()

    # ----- Signal emission -----

    def evaluate(self, ticker: str, now: datetime | None = None) -> SentimentSignal | None:
        ticker = ticker.upper().lstrip("$")
        state = self._tickers.get(ticker)
        if state is None or not state.mentions:
            return None

        now = now or datetime.now(timezone.utc)
        now_unix = now.timestamp()

        # Cooldown
        if now_unix - state.last_signal_unix < self.signal_cooldown:
            return None

        # Baseline: weighted mentions per minute over [now - baseline_window, now - signal_window]
        baseline_start = now_unix - self.baseline_window
        baseline_end = now_unix - self.signal_window
        baseline_mentions = [
            (t, w) for (t, w, _) in state.mentions if baseline_start <= t < baseline_end
        ]
        baseline_minutes = max(1.0, (baseline_end - baseline_start) / 60.0)
        baseline_weighted_total = sum(w for _, w in baseline_mentions)
        baseline_per_min = baseline_weighted_total / baseline_minutes
        if baseline_weighted_total < self.min_baseline_mentions:
            return None

        # Per-minute breakdown of baseline window for stdev
        minute_buckets: dict[int, float] = {}
        for t, w in baseline_mentions:
            bucket = int(t // 60)
            minute_buckets[bucket] = minute_buckets.get(bucket, 0.0) + w
        if len(minute_buckets) < 5:
            return None  # not enough variance data
        baseline_minute_counts = list(minute_buckets.values())
        # Pad with zeros for minutes with no mentions to get a realistic stdev
        zero_minutes = max(0, int(baseline_minutes) - len(baseline_minute_counts))
        baseline_minute_counts.extend([0.0] * zero_minutes)
        baseline_mean = mean(baseline_minute_counts)
        baseline_std = pstdev(baseline_minute_counts) if len(baseline_minute_counts) > 1 else 0.0
        if baseline_std == 0:
            # Perfectly uniform baseline (e.g. 1 mention/minute exactly) — use a
            # Poisson-style fallback so we still detect outliers. stdev ≈ sqrt(mean)
            # for a Poisson process; floor at 0.5 to avoid huge z-scores when
            # baseline is near zero.
            baseline_std = max(0.5, baseline_mean ** 0.5)

        # Signal window: weighted mentions in last signal_window seconds
        signal_start = now_unix - self.signal_window
        signal_mentions = [
            (t, w, s) for (t, w, s) in state.mentions if t >= signal_start
        ]
        if not signal_mentions:
            return None
        signal_weighted = sum(w for _, w, _ in signal_mentions)
        # Normalize to per-minute rate
        signal_per_min = signal_weighted * (60.0 / self.signal_window)

        z = (signal_per_min - baseline_mean) / baseline_std
        if z < self.z_threshold:
            return None

        # Correlation gate: did price already move with mentions in last 10 min?
        corr = self._compute_mention_price_correlation(state, now_unix)
        if corr is not None and abs(corr) >= self.max_price_correlation:
            # Already priced in
            return None

        # Source distribution
        contributing: dict[str, int] = {}
        for _, _, src in signal_mentions:
            contributing[src] = contributing.get(src, 0) + 1

        state.last_signal_unix = now_unix
        return SentimentSignal(
            ticker=ticker,
            z_score=float(z),
            mentions_last_minute=signal_per_min,
            mentions_per_min_baseline=baseline_per_min,
            correlation_with_price=corr,
            confidence=min(0.95, 0.4 + (z - self.z_threshold) * 0.05),
            suggested_hold_seconds=self.suggested_hold_seconds,
            triggered_at=now,
            contributing_sources=contributing,
        )

    def _compute_mention_price_correlation(self, state: _TickerState, now_unix: float) -> float | None:
        """Compute correlation between minute-bucketed mention counts and prices
        over the last 10 minutes. None if not enough data."""
        if len(state.prices) < 5:
            return None
        window_start = now_unix - 600  # 10 min
        # Bucket mentions and prices into 1-min buckets
        mention_buckets: dict[int, float] = {}
        for t, w, _ in state.mentions:
            if t < window_start:
                continue
            b = int(t // 60)
            mention_buckets[b] = mention_buckets.get(b, 0.0) + w
        price_buckets: dict[int, list[float]] = {}
        for t, p in state.prices:
            if t < window_start:
                continue
            b = int(t // 60)
            price_buckets.setdefault(b, []).append(p)

        common = sorted(set(mention_buckets.keys()) & set(price_buckets.keys()))
        if len(common) < 5:
            return None
        m = np.array([mention_buckets[b] for b in common])
        p = np.array([mean(price_buckets[b]) for b in common])
        if m.std() == 0 or p.std() == 0:
            return None
        return float(np.corrcoef(m, p)[0, 1])
