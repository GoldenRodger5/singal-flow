"""A5 — Sentiment velocity scanner.

Thesis:
  Crypto retail attention is a leading indicator on the 30s–10min timescale.
  When a coin/ticker's mention-rate suddenly spikes (z-score on rolling
  baseline), it's often because something is happening — a launch, a meme
  going viral, a coordinated pump. Price reaction lags mention spike by
  seconds to minutes; that lag IS the edge.

Sources (all free-tier API):
  1. X (Twitter) — requires developer account, free tier ~500 tweets/month
     (extremely tight). For shadow mode we use search-recent which has
     better quota. Production requires bumping to Basic tier ($100/mo) once
     we know we want to deploy this strategy live.
  2. Farcaster — Pinata or Neynar public API. Free.
  3. Telegram public channels — read via tdlib or by joining as a bot.
     For v1 we focus on X + Farcaster; Telegram comes later.
  4. Reddit /r/CryptoCurrency + /r/SatoshiStreetBets — free via PRAW.

Approach:
  * Stream / poll mentions of crypto tickers ($BTC, $SOL, $WIF, etc.)
  * Maintain rolling baseline of mentions per ticker (last 60 min)
  * Compute z-score of last 1-minute window vs baseline
  * When z > threshold AND on-chain liquidity exists for the ticker:
    emit a SentimentSignal

Edge attribution:
  This is NOT just "buy when people tweet" — it's "buy when mention rate
  ACCELERATES faster than price." If price has already moved, the signal is
  stale. Detector logic enforces the lag: mention spike must precede price
  spike by > 30 seconds AND the price-vs-mention correlation in the last
  10 minutes must be < 0.5 (otherwise it's just news already priced in).
"""
from helios.strategies.a5_sentiment.detector import (
    MentionEvent,
    SentimentDetector,
    SentimentSignal,
)

__all__ = ["MentionEvent", "SentimentDetector", "SentimentSignal"]
