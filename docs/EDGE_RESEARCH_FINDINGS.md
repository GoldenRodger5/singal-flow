# Helios Edge Research Findings

> Living record of every trading edge we've empirically tested, the verdict, and
> why. Read this before proposing or building a new strategy — don't re-test a
> dead edge. Last updated: 2026-05-29.

## TL;DR

Six edges tested against 15 months of real Kraken Futures + Solana data. **None
shows a robust, deployable, large-magnitude positive edge.** Two structural
truths emerged: (1) crypto perps mean-revert short-term, they do NOT trend;
(2) the real edges that exist are faint, market-neutral, single-digit-% — not
the asymmetric moonshot machine "$1k → thousands/month" requires.

This was found at **$0 capital risk** via shadow mode + backtesting. That is the
methodology working, not failing.

---

## The verdict table

| Edge | Mechanism | Verdict | Key number |
|---|---|---|---|
| **A1** crypto perp trend | XGBoost on momentum/vol features | ❌ DEAD | Gross Sharpe 1.84 → net −2 bps/bar after costs; 49% cross-symbol hit rate |
| **A2** memecoin sniping | Buy DexScreener-trending Solana launches | ❌ DEAD | Best exit (target3x/stop50) +2.9% at 0% slippage, −15.8% at 10%/leg. 81% of tokens finish negative |
| **A8** cash-and-carry | Long spot / short perp, harvest funding | ❌ FLAT (regime) | −0.36% APY; funding never exceeded 50% APY in the window. Pays only in high-funding frenzies |
| **Momentum** (x-sectional) | Long winners / short losers, 15-perp basket | ❌ DEAD | Negative in EVERY config; some Sharpe −10 |
| **Reversal** (x-sectional) | Long losers / short winners, market-neutral | ❌ DEAD (under honest validation) | Fixed 48h/24h looked great (rolling OOS Sharpe +2.10, DSR 1.0 @ n_trials=1) BUT Deflated Sharpe collapses to **0.42** (n=15 trials) / **0.24** (n=40) — multiple-testing artifact. Adaptive re-tuning (look-ahead-free) = **−0.18 Sharpe, −43%**. |
| **Funding reversion** | Fade funding-rate extremes | ⚠️ FAINT | Best +0.47%/signal (12h hold, z≥3.0, 53% win) — too small after real slippage |

---

## Structural findings (these are real, repeatable, not noise)

1. **Crypto perps mean-revert at short horizons; they do not trend.**
   Cross-sectional momentum lost in all 20 configs (some catastrophically,
   Sharpe −10). Reversal beat momentum everywhere. This is *why* A1
   trend-following failed and is the single most reliable pattern we found.

2. **Memecoin "moonshots" are a negative-EV trap.**
   27% of detected tokens hit 2x intra-window, 2.6% hit 10x — the tail is real.
   But 81% finish 24h negative (median −43%), and no exit policy clears positive
   EV at realistic slippage (5–20%/leg on thin memecoin books). The pump happens
   then dumps; capturing it requires sub-120s detection (paid Helius WS) we don't
   have. Even with perfect zero-cost execution the best policy is only +2.9%.

3. **Carry is regime-dependent.** Cash-and-carry funding harvest is mechanically
   sound but pays only when funding APY clears the round-trip cost (~26% APY at a
   5-day maker hold). The 2024–2026 window was structurally low-funding, so it was
   flat-to-negative. Keep it armed for high-funding regimes; don't expect income now.

4. **The real edges are faint and market-neutral.** Reversal and funding-reversion
   both show consistent-but-tiny positive signals (single-digit %). These are the
   honest "what works" — small, boring, market-neutral — not the asymmetric machine.

---

## Operational lessons (cost of running)

- **Birdeye free tier exhausts its compute-unit budget in ~2 days** of continuous
  OHLCV + holder fetching. Switched outcome harvesting to **GeckoTerminal** (free,
  no key, no observed CU cap). GeckoTerminal only indexes tokens that survived long
  enough to be tracked → DO NOT use it for exit research (survivorship bias); use
  stored outcomes computed when data was live.
- **Helius Atlas WebSocket (new-pool detection) is a PAID feature** — 403 on free
  tier. A2-live (fast launch detection) is therefore gated behind a paid plan.
  A2-live task is now opt-in (`--enable-a2-live`).
- **Coinglass v4 API requires a key** even for "public" endpoints — no truly free
  tier as assumed. A3 (liquidation hunter) blocked until `COINGLASS_API_KEY` set.
- **Warpcast public endpoint now 401s** — A5 (sentiment) needs `NEYNAR_API_KEY`
  for Farcaster and/or `X_API_BEARER` for X, else it has no data sources.

---

## What's still untested

- **A3 liquidation cascade hunting** — built, needs free Coinglass key.
- **A5 sentiment velocity** — built, needs free Neynar (and/or X) key.
- **Combined market-neutral book** (reversal + funding-reversion, validated with
  walk-forward + Deflated Sharpe) — the recommended next build. Faint edges combined
  + rigorously validated = the honest candidate for a small, real, scalable edge.
- **Paid first-120s memecoin detection** (Helius paid WS) — the one A2 angle not
  yet tested; ~$50/mo, uncertain payoff.

---

## The honest strategic conclusion

**"$1k → thousands/month autonomously via retail crypto" is not supported by the
evidence.** The achievable version is: *a small (single-digit-% monthly),
market-neutral edge that compounds and scales with capital.* On $1k that's
$20–50/mo. On $50k it's $1–2.5k/mo. The math only reaches "thousands/month" with
size, time, or a fundamentally different (likely non-retail-crypto) edge.

This does not mean stop — it means calibrate expectations to reality and build the
small real edge rather than chasing faint asymmetric mirages. Strategy #7/#8/#9 on
the same retail-crypto surface will, on this evidence, also be faint.
