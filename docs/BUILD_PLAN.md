# Helios Build Plan

> Companion to [REVOLUTION_PLAN.md](REVOLUTION_PLAN.md). This is the phased, falsifiable execution sequence. Each phase has an explicit exit criterion — if it fails the criterion, you do NOT advance.

---

## Phase 0 — Stop the bleeding (1–2 days)

Before any new work. These are the things that are dangerous right now.

- [ ] **Rotate every credential** in [.env](.env). The file is git-tracked. Assume all keys are compromised.
  - OpenAI, Anthropic, Alpaca, Polygon, Telegram, Twilio, MongoDB.
- [ ] **Move `.env` to a secrets manager** (1Password CLI / Doppler / Railway secrets). Add to `.gitignore` (verify it's there) and run `git rm --cached .env`.
- [ ] **Force `PAPER_TRADING=true`** as a compile-time constant in the new code path; live mode requires an explicit signed config artifact.
- [ ] **Freeze the legacy code.** Tag `legacy/signal-flow-v0` on `main`. Create `helios/` branch off it. No more edits to legacy services.
- [ ] **Consolidate requirements**: delete the 8 competing `requirements*.txt` files; replace with `pyproject.toml` + `uv` lockfile.

**Exit criterion:** Credentials rotated, paper-trading hard-locked, repo state is clean.

---

## Phase 1 — Foundation: data + backtest + risk overlay (2–3 weeks)

We build the floor before the building. No strategies yet.

### 1.1 Data plane
- [ ] `helios/data/` package. Adapters for: Polygon (equities), Kraken (crypto spot), Hyperliquid (crypto perps), Alpaca (equities exec), Coinbase (crypto exec).
- [ ] Tick + minute-bar history downloader → Parquet on local disk (later: S3/R2).
- [ ] DuckDB query layer with point-in-time guarantees (each bar has `available_at` ≤ `event_time`).
- [ ] News + filings ingestion: Polygon news + SEC EDGAR + a free crypto news API. Stored raw + with FinBERT embeddings.

**Exit criterion:** Can query "give me the OHLCV + features for symbol X as of timestamp T" with zero lookahead, for any X and T in the loaded window. Verified by an automated lookahead-leak test.

### 1.2 Backtest engine
- [ ] `helios/backtest/` — event-driven walker with realistic fill model: spread sampled from historical L1, slippage as `f(order_size / ADV)`, commission table per venue, partial fills, latency injection.
- [ ] Walk-forward harness: rolling 2y train / 6m val with configurable step.
- [ ] Purged k-fold CV (López de Prado) for any tabular model.
- [ ] Monte Carlo trade-order shuffle (≥ 1000 permutations) → distribution of Sharpe and max DD.
- [ ] Deflated Sharpe Ratio reporter (penalizes multi-testing).
- [ ] Tearsheet generator: HTML + PDF, attribution by strategy/asset/regime.

**Exit criterion:** Backtest a trivial benchmark (60/40 SPY/AGG, buy-and-hold BTC) and confirm Sharpe, DD, and turnover match published values within 5%.

### 1.3 Risk overlay
- [ ] `helios/risk/` — stateless function `risk_overlay(intent, portfolio_state, market_state) -> ApprovedOrder | Rejection`.
- [ ] Implements all rules from §4.4 of the revolution plan.
- [ ] **Property-based tests** (Hypothesis) for every rule. Coverage ≥ 90% on this module.
- [ ] Chaos test: inject synthetic gap, broker timeout, data outage. Verify kill switch fires.

**Exit criterion:** Test suite green. Manual review by you of every rule.

### 1.4 Control plane keep-alive
- [ ] Strip [railway_start.py](backend/railway_start.py) down to: health, auth, audit-log query, kill-switch endpoint, config read-only. Everything else moves under `helios/`.
- [ ] Cockpit (Next.js) gets a "system status" page wired to the new endpoints.

**Exit criterion:** Old UI loads, shows kill switch, shows audit log. No trade decisions yet.

---

## Phase 2 — First strategy + execution agent (3–4 weeks)

Pick the easiest-to-validate strategy: **crypto momentum / breakout on BTC/ETH/SOL perps.**

### 2.1 Strategy module
- [ ] `helios/strategies/crypto_momentum/` — feature pipeline (returns, vol, funding, OI deltas, perp-spot basis), signal model (gradient-boosted classifier on next-N-bar direction).
- [ ] Train on 2022–2024, walk-forward through 2025.
- [ ] Standard contract: `Strategy.signal(t) -> {symbol, direction, magnitude in [-1,1], confidence in [0,1], features_used}`.

### 2.2 Meta-allocator (skeleton)
- [ ] `helios/allocator/` — for v1 with one strategy, just translates signal → target weight via Kelly with the calibrated hit-rate / win-loss ratio.
- [ ] Connected through the risk overlay.

### 2.3 Execution agent v1
- [ ] `helios/execution/` — start with a deterministic VWAP slicer. PPO RL agent comes in Phase 4.
- [ ] Smart-order-routing across Kraken + Hyperliquid for the same asset.
- [ ] Records every fill: requested price, executed price, slippage, market state at submit/fill.

### 2.4 Paper trade
- [ ] 30 days continuous paper trading on a $10k notional book. All decisions, features, sizing, and fills logged.

**Exit criterion:** Strategy walk-forward Sharpe > 1.0 net of costs, max DD < 15%, ≥ 200 OOS trades. Paper-trade realized Sharpe within 30% of backtest Sharpe (otherwise the slippage model is wrong — fix it before continuing).

---

## Phase 3 — Ensemble (4–6 weeks)

Add the other four strategies from §4.2, one per sprint. Each must pass the same exit gate as Phase 2.

- [ ] Crypto basis arb
- [ ] Earnings-drift NLP (equities)
- [ ] Mean-reversion intraday (liquid ETFs)
- [ ] News-shock event

Then upgrade the meta-allocator:
- [ ] Online regime classifier (HMM on vol/correlation/breadth).
- [ ] Regime → strategy-eligibility map.
- [ ] Allocation: risk-parity within eligible strategies + Kelly-scaled overall gross.

**Exit criterion:** ≥ 3 of 5 strategies pass; ensemble walk-forward Sharpe > 1.2 net of costs; max DD < 12%; regime gate fires correctly in synthetic stress test.

---

## Phase 4 — Self-learning loop (3–4 weeks)

Now we earn the "AI autonomous" label.

### 4.1 RL execution agent
- [ ] `helios/execution/rl/` — PPO via Stable-Baselines3. Observation: parent order, book state, time-of-day, recent vol. Action: child-order size + delay. Reward: − implementation shortfall.
- [ ] Train in a replay simulator built from logged order books.
- [ ] A/B against the VWAP baseline. Promote only if it beats by ≥ 15 bps on held-out fills.

### 4.2 Online calibration
- [ ] Bayesian update of each strategy's hit-rate and win/loss after every closed trade → feeds Kelly.
- [ ] Drift monitor: KS test on feature distributions, PSI on signal output. Auto-bench any strategy whose PSI > 0.25.

### 4.3 Pattern memory
- [ ] Vector DB (Qdrant or pgvector). On each setup, embed the pre-trade feature vector + store outcome.
- [ ] At decision time, fetch k-nearest past setups → empirical outcome distribution surfaced in the cockpit ("97 similar setups, +0.6% mean, 54% hit-rate").

### 4.4 Nightly retrain job
- [ ] Cron (Railway / GitHub Actions): walk-forward retrain each strategy; Optuna hyperparam search bounded by OOS Sharpe; commit new model artifact under a version tag; old models kept N=10 for rollback.

**Exit criterion:** RL agent beats VWAP. Drift monitor catches a deliberately-introduced regime change in a chaos test. Nightly job runs unattended for 14 days with green tearsheets.

---

## Phase 5 — Cockpit upgrade (parallel to Phase 3–4, ~2 weeks)

Make the Next.js UI an actual quant cockpit, not a holdings table.

- [ ] Live P&L with strategy attribution
- [ ] Regime indicator (current state + transition probabilities)
- [ ] Signal panel per strategy (raw signal, sized signal, blocked-by-risk flag)
- [ ] Fill quality view (slippage vs. model, broken down by venue/asset/size bucket)
- [ ] Pattern-memory similarity panel ("you have seen this 97 times before")
- [ ] Manual kill switch + audit-log viewer
- [ ] Nightly tearsheet viewer (rendered from artifacts)

**Exit criterion:** You can sit in front of the cockpit during a paper-trading session and explain every decision the system made in the last hour without opening a code file.

---

## Phase 6 — Live capital, slowly (ongoing)

This is a ramp, not a switch.

- [ ] Week 1–2: $500 notional, single strategy (crypto momentum). Halt at −5% drawdown.
- [ ] Week 3–4: $1k, two strategies.
- [ ] Month 2: $5k, full ensemble, halt at −10% drawdown.
- [ ] Month 3+: scale by 1.5× per month *only* if realized Sharpe > 0.8 and risk-overlay breach count == 0.

At every step: if realized Sharpe is < 50% of paper Sharpe, **stop**. Investigate the slippage / regime / market-impact assumption that's wrong before adding more capital.

---

## Cross-cutting work

### Testing
- Unit tests for every numeric helper (indicators, sizing, slippage model).
- Property-based tests for risk overlay (Hypothesis).
- Integration test: replay one day of historical ticks through the full pipeline, assert deterministic output.
- Chaos tests: synthetic gap, broker timeout, data outage, NaN feature, duplicate fill, partial fill mid-cancel.

### Ops
- Structured logging (loguru → JSON → file + stdout).
- Metrics (Prometheus or OpenTelemetry) for signal latency, fill latency, queue depth, error rate.
- Alerting: PagerDuty-style routing of P0 events (kill switch fired, drift detected, broker disconnect).
- DR plan: daily Parquet backup of trades + audit log to two regions; documented runbook for restoring from cold start.

### Governance
- Weekly tearsheet review (you + a journal).
- Per-strategy decommissioning rule: if 30-day rolling Sharpe < 0 and PSI > 0.25, auto-bench, human review required to re-enable.
- Quarterly external review: send anonymized backtest + tearsheets to a quant friend for sanity check.

---

## Timeline summary

| Phase | Duration | Cumulative |
|---|---|---|
| 0 — Stop the bleeding | 1–2 days | week 1 |
| 1 — Foundation | 2–3 weeks | week 4 |
| 2 — First strategy + execution | 3–4 weeks | week 8 |
| 3 — Ensemble | 4–6 weeks | week 14 |
| 4 — Self-learning | 3–4 weeks | week 18 |
| 5 — Cockpit | ~2 weeks (parallel) | week 18 |
| 6 — Live ramp | ongoing | month 5+ |

**Realistic first live dollar: ~4 months in.** Anyone telling you faster is selling something.

---

## Decision log template

Each significant choice gets a row in `docs/decisions.md`:

```
- 2026-05-24 — Chose XGBoost over LSTM for crypto momentum signal.
  Why: tabular features dominate; XGBoost trains 50× faster; LSTM didn't beat it in walk-forward (Sharpe 1.1 vs 1.3).
  Revisit when: we add order-book sequential features.
```

This is how we avoid re-litigating settled choices and how future-you (or a collaborator) understands the system.

---

## What's intentionally NOT in v1

- HFT / sub-millisecond strategies — wrong substrate (Python, Railway, Alpaca).
- Options Greeks / vol-surface trading — adds a full asset class of complexity.
- Social-sentiment / Twitter scraping as primary signal — too noisy, too gameable.
- A frontier LLM in the synchronous trade loop — known anti-pattern (StockBench).
- Multi-account / multi-tenant — solo operator only until edge is proven.
- Shorting equities below $5 — borrow availability is unreliable, risk-reward is terrible.

These are deferred deliberately. The point of v1 is to prove the edge exists and the system can survive its own mistakes. Everything else is scope creep.
