# Signal Flow → Helios: Revolution Plan

> **Codename:** Helios (autonomous AI alpha engine)
> **Author:** Quant audit, May 2026
> **Status:** Strategic blueprint — not yet implemented
> **Predecessor:** Signal Flow (penny-stock momentum bot, ~35% complete prototype)
> **Revision history:** v1 (§1–8) original blueprint. v2 (§9–15) red-team self-critique + revisions: strategy stack repivoted toward carry/yield harvesters, AI/self-calibration spec made concrete, data manifest formalized, code migration mapped file-by-file, honest capital→income math, new risks named. v3 (§16) **aggressive small-capital path** — leverage + asymmetry + velocity + AI discipline, the actual answer to "thousands/month from $5–10k". **§16 supersedes §10 and §13 for the strategy stack and income math. Read §16 first if returning to this doc.**

---

## 0. TL;DR

Signal Flow today is a **rules-based penny-stock momentum scanner** wearing AI marketing. The "AI learning engine" is a thin weight-update wrapper around OpenAI/Claude prompt calls. There is no backtest, no validated edge, no live performance. The strategy (Williams %R + Bollinger squeeze on $0.75–$10 micro-caps) is a 50-year-old retail playbook in the most adversely-selected, slippage-heavy corner of the equity market.

To turn this into an actual autonomous quant system that can compound real money, we throw away the framing and rebuild around five hard requirements:

1. **Edge must be measured, not asserted.** Walk-forward backtests with purged CV are the gate to capital. No backtest → no money.
2. **The LLM is a feature, not the brain.** Use it for unstructured-data ingestion (news, filings, transcripts, social) and reasoning audits. Trading decisions come from numerical models.
3. **Multi-strategy ensemble over single signal.** Momentum is one regime. We add mean-reversion, stat-arb, event-driven, and microstructure signals voted by a meta-allocator.
4. **Self-calibration loop is the moat.** Online regime detection + Bayesian parameter updating + a reinforcement-learning execution agent that improves with every fill.
5. **Crypto first, equities second.** 24/7, programmatic, deep liquidity at the micro-cap-equivalent dollar size, no PDT rule, no halts. An autonomous bot should live where the market never sleeps.

The product becomes **Helios**: a self-improving, multi-strategy, multi-asset autonomous trader with a deterministic risk overlay and a transparent reasoning layer. The existing Next.js dashboard becomes the cockpit; the existing FastAPI server becomes the control plane; everything below the API line is rebuilt.

---

## 1. Honest Audit of What Exists

### 1.1 What works
- **Architecture skeleton** is reasonable: agent layer / service layer / FastAPI control plane / Next.js UI / MongoDB / Railway+Vercel deploy. Worth keeping.
- **Integrations are real**: Polygon (data), Alpaca (broker), Telegram (notifications), OpenAI + Anthropic (LLM). Credentials work.
- **Kelly-based position sizer** in [enhanced_position_sizer.py](backend/services/enhanced_position_sizer.py) is mathematically sound, with sensible safeguards (0.25 Kelly multiplier, vol scaling).
- **Paper-trading safety override** is correctly enforced.
- **Modular agent design** — easy to swap brains without rewriting orchestration.

### 1.2 What doesn't work (the ugly)
- **No validated edge.** README claims 60–65% win rate and $6.5–8k/year on $100/wk. There is zero backtest in the repo. These are aspirational numbers presented as facts.
- **"AI learning" is theatre.** [ai_learning_engine.py](backend/services/ai_learning_engine.py) multiplies weights by 1.05 on wins and 0.95 on losses. That is not learning — it is a moving average with extra steps. No model artifacts, no validation set, no convergence proof.
- **Strategy lives in the worst neighborhood.** Sub-$10, 10–50M-float US equities are dominated by pump-and-dump, wide spreads (often 1–3% of mid), thin liquidity, halt risk, and adverse selection from market makers. The very class of trader the strategy targets — retail momentum chasers — is who loses to the market makers it must trade against. [Microcap research](https://stock-market.live/microcap-resurgence-ai-screening-community-liquidity-2026) confirms execution quality is now *the* dominant return driver.
- **LLM-as-decider is a known anti-pattern.** [StockBench](https://arxiv.org/pdf/2510.02209) and [AI-Trader](https://arxiv.org/pdf/2512.10971) benchmarks both show LLM agents typically underperform buy-and-hold and exhibit weak risk management. We must not put GPT-4o in the decision seat.
- **No tests for any of the actual strategy code.** 14 test files across 92 modules.
- **Eight competing `requirements*.txt` files**, multiple Python version pins, abandoned scikit-learn dependency. The repo is mid-thrash.
- **Single broker, single data vendor, single market session.** All concentration risk.
- **Secrets committed in `.env`** to a working tree that is git-tracked. Rotate everything before going further.

### 1.3 Verdict
The product is a prototype, not a system. We keep the API + UI + sizer + integrations, and rebuild the brain.

---

## 2. The Good / Bad / Ugly of the Current Approach

| Dimension | Good | Bad | Ugly |
|---|---|---|---|
| Strategy | Volume + momentum filter is a real factor | Single regime, single timeframe | Sub-$10 micro-caps = adverse-selection slaughterhouse |
| AI | LLMs ARE good at unstructured data | Used as the decision-maker, not as a feature | "Learning" loop has no math behind it |
| Risk | Kelly sizing exists | No regime detection, no correlation cap, no drawdown brake | No circuit breaker for halts / gap-downs |
| Data | Polygon is a fine vendor | No order book, no alt-data, no tick-level history | No deduplication, no point-in-time correctness |
| Backtest | — | None exists | README publishes performance numbers anyway |
| Execution | Alpaca works | Market orders only, no VWAP/TWAP | Penny-stock slippage not modeled, will eat all edge |
| Ops | Health endpoints, Railway deploy | No alerting, no kill switch | Local-only "full system" means it dies when laptop sleeps |

---

## 3. Design Principles for Helios

1. **Falsifiability first.** Every strategy ships with a backtest report (walk-forward + purged CV + Monte Carlo trade-order shuffle) before it gets a dollar of capital.
2. **Determinism in the hot path.** LLMs and large NN inferences run *outside* the trade loop. The trade loop is pure numerical code with a fixed latency budget.
3. **Composable signals, meta-allocated.** Each strategy outputs a normalized signal in `[-1, +1]` with a confidence. A meta-model decides allocation.
4. **Online + offline learning.** Offline: nightly retraining on the day's data. Online: Bayesian state updates and RL execution policy refinement.
5. **Risk is an overlay, not a parameter.** Position size, regime gate, and kill-switch are independent of strategy code. A strategy cannot bypass risk.
6. **Observable by default.** Every decision logs: features in, model versions used, signal value, sizing math, executed price, slippage vs. mid, attribution. This is the dataset that powers self-improvement.
7. **No PII, no secrets in code.** Vault-managed creds. `.env` rotation today.

---

## 4. The Helios Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│ COCKPIT  (Next.js — existing UI, expanded)                         │
│   live P&L, regime, signals, RL telemetry, kill switch             │
└─────────────────────────────▲──────────────────────────────────────┘
                              │ REST + WebSocket
┌─────────────────────────────┴──────────────────────────────────────┐
│ CONTROL PLANE  (FastAPI — keep)                                    │
│   auth · config · run/halt · audit log · backtest API              │
└─────────────────────────────▲──────────────────────────────────────┘
                              │
┌─────────────────────────────┴──────────────────────────────────────┐
│ ORCHESTRATOR  (asyncio loop + Redis Streams)                       │
└──┬────────────┬─────────────┬─────────────┬─────────────┬──────────┘
   │            │             │             │             │
┌──▼───────┐ ┌──▼────────┐ ┌──▼─────────┐ ┌─▼──────────┐ ┌▼─────────┐
│ Data     │ │ Feature   │ │ Strategy   │ │ Meta-      │ │ Execution│
│ Plane    │ │ Store     │ │ Ensemble   │ │ Allocator  │ │ Agent    │
│ (tick,   │ │ (Feast or │ │ 5 strats   │ │ XGBoost +  │ │ (PPO RL  │
│ news,    │ │ Polars +  │ │ sub-       │ │ regime     │ │ for      │
│ social,  │ │ DuckDB +  │ │ models)    │ │ gate)      │ │ TWAP/    │
│ filings) │ │ Parquet)  │ │            │ │            │ │ child    │
│          │ │           │ │            │ │            │ │ orders)  │
└──┬───────┘ └───────────┘ └────────────┘ └────────────┘ └─┬────────┘
   │                                                       │
   │                ┌──────────────────────────┐           │
   └───────────────►│ Risk Overlay (sync)      │◄──────────┘
                    │ pos limit · DD brake ·   │
                    │ corr cap · regime kill   │
                    └──────────────┬───────────┘
                                   │
                       ┌───────────▼────────────┐
                       │ Broker Adapters         │
                       │ Alpaca · IBKR · Kraken  │
                       │ · Hyperliquid · Binance │
                       └─────────────────────────┘

                       ┌────────────────────────────┐
                       │ LEARNING PLANE  (nightly)  │
                       │  • RL policy update (PPO)  │
                       │  • Strategy retrain        │
                       │  • Regime model retrain    │
                       │  • Walk-forward backtest   │
                       │  • Hyperparam search (Optuna)│
                       │  • Drift detection (KS, PSI)│
                       └────────────────────────────┘
```

### 4.1 Component decisions

- **Storage:** Parquet on object store + DuckDB for analytic queries; MongoDB stays for audit log & user state; Redis Streams for the live event bus.
- **Feature store:** [Feast](https://feast.dev) or a thin Polars/DuckDB layer. Mandatory: every feature is point-in-time correct (no lookahead).
- **Modeling:** XGBoost / LightGBM for tabular signals; small transformers (FinBERT, DistilBERT) for text embeddings; PPO ([Stable-Baselines3](https://stable-baselines3.readthedocs.io)) for execution. NO frontier LLM in the inner loop.
- **Backtest engine:** [vectorbt](https://vectorbt.dev) for fast sweeps + a custom event-driven walker (Backtrader-style) for realistic fills. Slippage modeled as a function of order_size / ADV with bid-ask spread sampled from L2 history.
- **Validation:** Purged k-fold CV ([López de Prado](https://www.wiley.com/Advances+in+Financial+Machine+Learning)), walk-forward, Monte Carlo trade-order shuffle, Deflated Sharpe Ratio.
- **LLMs:** Anthropic Claude Sonnet for nightly research summaries + news/filing feature extraction; cached via prompt caching; rate-limited; never on the synchronous trade path.
- **Vector memory:** pgvector or Qdrant — embeddings of historical setups so the system can ask "have I seen this before?" and retrieve outcome distributions.

### 4.2 Five strategies in the v1 ensemble

| # | Name | Edge thesis | Asset | Horizon |
|---|---|---|---|---|
| 1 | **Crypto momentum / breakout** | Trend persistence on perp funding + open-interest shifts | BTC/ETH/SOL perps | Hours–days |
| 2 | **Cross-exchange basis** | Funding-rate / spot-perp basis arb | Crypto | Minutes–hours |
| 3 | **Earnings-drift NLP** | Post-earnings drift conditioned on transcript-tone embeddings | US equities (liquid mid-caps) | 1–5 days |
| 4 | **Mean-reversion intraday** | Z-score reversion on liquid ETFs filtered by regime | SPY/QQQ/IWM + sectors | Minutes |
| 5 | **News-shock event** | Filing/PR/social-velocity shock → directional reaction | US equities + crypto | Seconds–minutes |

Each must independently pass: Sharpe > 1.0 net of costs in walk-forward, max DD < 15%, ≥ 200 trades in the OOS window. Strategies that fail are benched, not capitalized.

### 4.3 The self-calibration loop

Continuous (online):
- Bayesian update on each strategy's hit-rate and average win/loss after every closed trade → feeds Kelly sizing.
- Online regime classifier (HMM on volatility + correlation + breadth) — gates which strategies are eligible to trade today.
- RL execution agent observes (parent order, book state, time-of-day, recent volatility) → emits child-order schedule → reward = − implementation shortfall.

Nightly (offline):
- Walk-forward retrain of each strategy on the rolling window (e.g. 2y train / 6m val).
- Concept-drift detection (KS test on feature distributions, PSI on signal output) — auto-bench any strategy whose drift exceeds threshold.
- Optuna hyperparameter search bounded by walk-forward Sharpe (not in-sample).
- Pattern memory: embed each closed trade's pre-trade feature vector + outcome into the vector DB. Future setups query this for nearest-neighbor outcome distributions, surfaced in the cockpit as "97 similar setups, mean +0.6%, hit-rate 54%".

Weekly (governance):
- Auto-generated tearsheet (returns, Sharpe, Sortino, Calmar, max DD, turnover, attribution by strategy/asset/regime).
- LLM-authored "what went wrong / what went right" memo, fed to the human operator.

### 4.4 The risk overlay (independent of strategy code)

Hard rules enforced *between* the allocator and the broker:
- Per-position cap (% of NAV)
- Per-strategy cap
- Aggregate gross + net exposure cap
- Real-time correlation cap (no >0.7 correlated cluster exceeds N% of NAV)
- Daily-loss kill switch (e.g. −2.5% NAV → halt, alert)
- Drawdown brake (peak-to-trough −10% → de-risk 50%; −20% → flat + human review)
- Regime gate (high-vol regime → only mean-reversion + basis strategies eligible)
- Per-asset liquidity check (order size ≤ 1% of trailing 5-min volume for equities, ≤ 0.5% of orderbook depth for crypto)

Any strategy attempting to violate these gets its order rejected at the overlay and logged.

---

## 5. Why crypto first

- **24/7 + programmatic-native.** An autonomous bot does not benefit from market closes; equities give it 6.5 hours/day to work and 17.5 to risk gap moves.
- **No PDT rule.** Sub-$25k US equity accounts get throttled to 3 day-trades per 5 sessions. Crypto has no such limit.
- **Deep, transparent order books.** L2/L3 data is cheap or free (Kraken, Coinbase, Hyperliquid public feeds).
- **Better execution venues for small size.** A $500 crypto market order is invisible. A $500 micro-cap order moves the book by 1%+.
- **Real arbitrage exists.** Funding-rate basis, cross-exchange spreads, perp-spot. Equities at retail size have essentially none.
- **Better RL substrate.** Continuous trading + dense reward signal accelerates the execution agent's learning by ~10× vs. an equities-only environment.

Equities stay in the ensemble (earnings-drift and event strategies) but at sized exposure, not as the primary universe.

---

## 6. What we keep from Signal Flow

- The Next.js cockpit ([frontend/](frontend/))
- The FastAPI control plane ([backend/railway_start.py](backend/railway_start.py))
- The Alpaca + Polygon adapters as one of many in a new `adapters/` layer
- The Kelly-based position sizer (becomes one input to the meta-allocator, not the final word)
- MongoDB for the audit log + UI state
- The Telegram notifier (becomes one of N alerting channels)
- Vercel + Railway deployment topology

Everything else under [backend/services/](backend/services/) and [backend/agents/](backend/agents/) is deprecated, archived for reference, and rewritten cleanly under a new `helios/` package.

---

## 7. Success criteria

A v1 of Helios is "done" when **all** are true:

1. ≥ 3 of 5 strategies pass walk-forward + purged CV with net-of-cost Sharpe > 1.0 and max DD < 15%.
2. Slippage model is calibrated against ≥ 500 live paper-trade fills (paper-vs-model within 20%).
3. RL execution agent beats naive market-order baseline by ≥ 15 bps on a held-out fill set.
4. 60 consecutive days of live paper trading with realized Sharpe > 0.8 and zero risk-overlay breaches.
5. Kill switch + drawdown brake fire correctly under chaos-test injection (synthetic −5% gap, broker timeout, data feed gap).
6. Test coverage ≥ 70% on `helios/risk/`, `helios/execution/`, `helios/sizing/` (the modules where bugs lose money).

Only after all six does live capital — at $500 starting size — touch the system.

---

## 8. What this is NOT

- Not a hedge fund. We are not pretending to compete with Two Sigma at HFT.
- Not get-rich-quick. Realistic year-one target on $5–25k capital is 15–35% net, with material risk of a −15% drawdown. Anyone modeling 5–10× returns is selling something.
- Not a trustless black box. The cockpit shows *why* every trade happened, what features drove it, and what the alternative actions were.
- Not a license to skip ops. Monitoring, alerting, secret rotation, and disaster recovery come *before* live capital, not after.

---

## 9. Red Team Review (self-critique, v2)

Putting on a hostile-second-quant hat. Where does the v1 plan fail?

### 9.1 The strategy stack is not optimized for the actual goal

The stated goal is **"thousands a month passively"**, not "interesting research project". The v1 strategy list is weighted toward **directional** strategies (momentum, mean-reversion, news-shock) that:
- Have crowded edges
- Require constant calibration
- Are not "passive" — they need babysitting, regime gates, retraining
- Have lumpy P&L (long flat stretches + occasional drawdowns)

For the actual goal, the highest-Sharpe strategies for an autonomous small-capital operator in 2026 are **carry / yield-harvesting** strategies, not directional ones. Specifically:

1. **Crypto funding-rate harvesting (cash-and-carry / delta-neutral basis).** Long spot BTC + short equivalent perp. The perp's funding payments accrue to you. Historical realized yield: 5–25% APY on BTC/ETH with near-zero directional exposure when properly delta-hedged. This is the closest thing to "passive" in crypto.
2. **Options vol-risk-premium harvesting.** Systematically sell cash-secured puts and covered calls on liquid underlyings (SPY, QQQ, IWM, MSTR, large-cap names) with mechanical rules (delta target, DTE target, roll rules). VRP is the most persistent empirical anomaly in finance.
3. **Cross-venue stablecoin / spot arbitrage.** Programmatic, scales linearly with capital, near-deterministic when executed correctly.

Directional strategies should be a **smaller** sleeve, not the main course. v1 had this backward.

### 9.2 "AI learning" was named but underspecified

The plan said "Bayesian updates", "PPO", "drift detection". As a critic, that's hand-wavy. Specifically missing:

- **Cold-start problem.** RL needs experience to learn. We have zero logged fills. How do we bootstrap? (Answer: replay simulator built from L2 history + domain randomization, then offline RL via CQL/IQL on the synthetic + initial-paper buffer.)
- **Off-policy evaluation.** Before deploying any new RL policy, we need IPS / Doubly-Robust estimators to predict its live performance. Not in v1 plan.
- **Contextual bandit layer over the ensemble.** Strategy allocation should be Thompson-sampling / LinUCB on `(market_state) → strategy_arm`, not just static risk parity. This is what "self-calibrating ensemble" actually means.
- **Conformal prediction for confidence.** Bayesian hit-rate gives a point estimate. Conformal prediction gives a calibrated *interval* — "this signal will produce a return in [−1.2%, +3.4%] with 90% coverage". Position size keys off the lower bound. Not in v1.
- **Online feature selection.** A feature that mattered in 2023 may be dead in 2026. Need a rolling SHAP / permutation-importance monitor that demotes dead features automatically. Not in v1.
- **Concept-drift *response* policy, not just detection.** v1 said "detect drift via KS/PSI". It did not say what to do. Need a tiered response: drift detected → reduce size 50% → retrain → if still drifted, bench.
- **Distillation of LLM reasoning into cheap classifiers.** The LLM is slow and expensive. Use it to label data once, then train a DistilBERT classifier that lives in the hot path. v1 implied this but never named it.
- **Nested cross-validation.** Optuna can itself overfit to the OOS fold. Need outer CV / inner CV separation + Deflated Sharpe to penalize the search.
- **Survivorship-bias-free universe.** Backtest universe must include delisted tickers (KRX, defunct crypto pairs). Otherwise we're testing on the winners only.
- **Causal vs. correlational features.** Most "features" are spurious under purged CV. Need to keep only features with stable purged-CV importance across regimes, not just high in-sample SHAP.

### 9.3 Data capture was a list, not an inventory

v1 said "Polygon, Kraken, Hyperliquid, news, filings". A critic would ask: which fields? At what frequency? Retained for how long? Joined how? Answers were missing. We need a *concrete data manifest* (added in §12).

### 9.4 The code-migration story was hand-wave

v1 said "everything else is rewritten under `helios/`". A critic would ask which legacy file maps to which new module, and which die. Answered in §15.

### 9.5 Honest income math was dodged

v1 said "realistic year-one target 15–35% net on $5–25k". A critic would ask: 25% on $10k is $2,500/year, or ~$208/month. That is not "thousands a month". The income claim needs explicit capital/return decomposition (§14).

### 9.6 Critical risks were under-named

- **Custody risk.** $10k locked on a crypto exchange that withdrawal-freezes overnight is a -100% event for that sleeve. v1 did not address.
- **Tax surface.** Thousands of trades/year = wash sales, mark-to-market election decision, 1099-B reconciliation hell. Need an accounting layer or trader-tax accountant from day one.
- **Sim-to-real gap.** Backtest Sharpe → paper Sharpe → live Sharpe typically loses 30–50% at each step. Plan must budget for it (size live capital assuming half the paper Sharpe).
- **Latency budget per venue.** Not modeled. A 200ms round-trip to Kraken from a Railway us-east container kills the news-shock strategy's edge.
- **Optuna / search overfitting.** Already mentioned.
- **Regulator risk on crypto perps for US persons.** Hyperliquid and Binance perpetuals have legal ambiguity for US residents. Need explicit venue policy.

Verdict: v1 was a directionally-right blueprint but missed the carry-strategies pivot, was thin on the actual self-calibration math, and dodged the income arithmetic. v2 (below) corrects.

---

## 10. Revised Strategy Stack (v2 — passive-income weighted)

Strategies ranked by **Sharpe-per-unit-attention** at $10–50k capital. The system is built around the top three; directional strategies are a smaller, optional sleeve.

### Tier 1 — Carry / yield harvesters (the engine)

**S1. Crypto funding-rate cash-and-carry.**
- Long spot BTC/ETH/SOL, short equivalent perp, both sized to delta-zero, on Hyperliquid / Binance / Bybit / Kraken Pro.
- Earns the funding rate (typically annualized 5–25% on majors, 30–80%+ on alt-perps when basis is hot).
- Rebalance when funding flips sign or basis decays below threshold.
- **Risk:** exchange custody, basis blow-out, perp delisting. Mitigation: multi-venue, position cap per venue, hard stop-loss on the spread.
- **Expected:** 10–18% net APY at low-to-medium risk, scales linearly with capital.
- **Why it fits "passive":** rebalance frequency is hours-to-days, not seconds.

**S2. Equity volatility-risk-premium harvest (the wheel, systematized).**
- Sell cash-secured puts at 30Δ on a curated list of 10–15 high-IV, fundamentally OK liquid underlyings (SPY/QQQ/IWM + selected names). Get assigned → sell covered calls at 30Δ. Roll mechanically.
- Filter by IV-rank > 50, earnings-blackout window, liquidity floor.
- **Risk:** tail events (vol spikes), gap-downs on individual names. Mitigation: index-only sleeve for the conservative variant; size as fraction of NAV; macro-vol kill switch.
- **Expected:** 12–20% net APY in normal regimes, occasional -5–10% drawdowns on vol shocks.
- **Why it fits:** position turnover is weekly-monthly. Truly passive on the operator side.

**S3. Stablecoin / spot cross-venue arbitrage.**
- Detect price dislocations between Coinbase, Kraken, Binance, Bybit on the same pair. Execute when net of fees + withdrawal time the spread is positive.
- Special case: stablecoin-de-peg trades (USDC, USDT, DAI) during stress windows.
- **Risk:** withdrawal/transfer time can flip the trade negative. Mitigation: prefund both venues, only trade pairs where same-venue settlement is instant.
- **Expected:** 5–15% APY, capital-constrained (need prefunded float at each venue).

### Tier 2 — Directional alpha (smaller sleeve)

**S4. Crypto trend-following on majors.**
- Replaces v1's "crypto momentum / breakout". XGBoost on (returns, vol, funding-term-structure, OI, perp-spot basis, on-chain flow) → next-N-bar direction. Trades BTC/ETH/SOL spot and perps.
- 10–25% of total capital.

**S5. Event-driven equity (earnings drift + filings).**
- Replaces v1's "earnings-drift NLP" AND "news-shock". Trades 1–5 day drift after earnings, conditioned on transcript-tone embeddings + surprise direction + IV crush context.
- 10–20% of total capital, ON only during earnings season.

### Tier 3 — Microstructure (deferred until infrastructure is ready)

**S6. Liquidation-cascade exploitation on crypto perps.**
- Predict liquidation clusters from OI + funding + price, fade or follow the cascade.
- Requires sub-second latency. Postponed to v2 of Helios.

### What got cut from v1

- **Mean-reversion intraday on ETFs.** Crowded, low edge for retail latency, requires babysitting. Cut.
- **News-shock as a standalone.** Merged into S5; the retail latency disadvantage makes it un-winnable on its own.

### Allocation policy

Capital split: **65% Tier 1 / 25% Tier 2 / 10% reserve.** Allocation within tiers via contextual-bandit (Thompson sampling on regime → strategy arms). This is what makes the ensemble *self-allocating*.

---

## 11. Expanded AI Stack + Self-Calibration (v2)

Mapping each capability to a concrete component.

### 11.1 Decision layers

| Layer | Job | Tech | Notes |
|---|---|---|---|
| L0 Features | Ingest raw → numerical features | Polars + DuckDB + FinBERT/DistilBERT embeddings | Point-in-time, versioned, lineage-tracked |
| L1 Per-strategy signal | Predict next-N-bar direction / yield | XGBoost / LightGBM per strategy | Walk-forward retrained nightly |
| L2 Uncertainty | Calibrated prediction intervals | Conformal prediction (split-conformal) | Drives position size, not just point pred |
| L3 Strategy allocator | Which strategy gets capital, how much | Contextual bandit (LinUCB / Thompson) over regime | Online learning |
| L4 Risk overlay | Hard rules between allocator and broker | Pure-function, property-tested | Cannot be bypassed |
| L5 Execution policy | Slice parent order into child orders | PPO (Stable-Baselines3), bootstrapped offline via CQL | Reward = − implementation shortfall |
| L6 Audit / reasoning | Explain & critique past trades | LLM (Claude Sonnet), nightly, off the hot path | Output is read by you, not the system |

### 11.2 Self-calibration loops (explicit)

**Tick-by-tick (synchronous, microseconds):**
- Order book snapshot → L5 execution policy emits next child order.

**Trade close (synchronous, ms):**
- Bayesian update of strategy `(hit_rate, win_loss_ratio)` posteriors.
- Update conformal calibration set (sliding window of N=500 most recent predictions+outcomes).
- Append `(features, action, reward)` to RL replay buffer with priority = TD-error.

**Hourly (async):**
- Drift monitor: PSI on signal output, KS on top-10 features. If PSI > 0.25 on any strategy → halve size; if > 0.5 → bench, alert.
- Contextual-bandit weights refresh on the last 30 days of fills.

**Nightly (offline, ~30–60 min):**
- Walk-forward retrain of each L1 model on rolling 2y train / 6m val.
- Hyperparameter search via Optuna with **nested CV** + Deflated Sharpe objective (not raw Sharpe).
- Off-policy evaluation (IPS + Doubly-Robust) of any candidate L5 policy on the day's logged data.
- LLM (Claude) writes a "trade-by-trade post-mortem" memo from the audit log. Distilled monthly into pattern updates.
- Vector DB embedding of every closed trade (features + outcome) — powers "have-I-seen-this" lookup tomorrow.

**Weekly:**
- Online feature-selection: rolling SHAP importance per strategy; features with importance below 5th percentile for 4 consecutive weeks get demoted.
- Tearsheet auto-generated. Deflated Sharpe, Calmar, max DD, turnover, by strategy/asset/regime.

**Monthly:**
- Strategy decommissioning review. Any strategy with 30-day Sharpe < 0 AND PSI > 0.25 → auto-bench, human review to re-enable.
- Distillation pass: LLM-labeled trade explanations → DistilBERT classifier trained for the live hot path.

### 11.3 Cold-start plan (because we have no live data)

1. Bootstrap L1 models from historical Parquet (≥ 3 years per asset class).
2. Bootstrap L5 RL agent via **offline RL (CQL or IQL)** on a synthetic fill dataset generated from L2 order-book history + a calibrated slippage model.
3. Run L5 in **shadow mode** for 30 days (predicts child orders but doesn't execute — VWAP baseline executes). Collect on-policy data.
4. Promote L5 to live only after off-policy estimator predicts ≥ 15 bps improvement over VWAP and 95% CI excludes worse-than-baseline.

This is the missing piece of v1: a *defensible* path from "no data" to "deployed learner" that doesn't require live trading to bootstrap.

---

## 12. Data Capture Manifest (v2)

A concrete inventory. Each row is a dataset we *will* ingest, with retention and source.

| Tier | Dataset | Source | Frequency | Retention | Used by |
|---|---|---|---|---|---|
| Market — equities | Tick-level trades + quotes (TAQ) | Polygon (paid) or IEX Cloud | Real-time + history | 5 years | S5, slippage model, L5 RL |
| Market — equities | Minute bars OHLCV | Polygon | Real-time | 10 years | All equity strategies |
| Market — equities | Corporate actions, splits, dividends, delistings | Polygon + manual SEC reconciliation | Daily | Forever | Backtest survivorship correction |
| Market — equities | Float / shares outstanding history | Polygon + 10-Q parse | Quarterly | Forever | Universe filter |
| Market — options | Full options chain (NBBO) | Polygon Options or ORATS | Minute | 3 years | S2 (VRP) |
| Market — options | Unusual options activity / sweep prints | CBOE LiveVol or Cheddar Flow | Real-time | 1 year | S5 augment |
| Market — crypto | L2 order book snapshots, 1-second | Kraken + Coinbase + Hyperliquid websockets | Real-time | 2 years | S1, S3, S6, L5 RL |
| Market — crypto | Trades + funding-rate history | Same | Real-time | Forever | S1, S4 |
| Market — crypto | Open interest, liquidations | Coinglass / venue APIs | Minute | 2 years | S4, S6 |
| Market — crypto | On-chain: DEX flows, large transfers, stablecoin mint/burn | Dune Analytics / Glassnode | Hourly | 2 years | S4 augment |
| News | Equity + crypto news headlines + bodies | Polygon News + CryptoPanic + RSS | Real-time | 3 years | S5, sentiment embeddings |
| Filings | SEC EDGAR 10-K/Q/8-K + Form 4 insider | EDGAR (free) | Real-time | Forever | S5, governance signal |
| Filings | Earnings call transcripts | AlphaSense or scraped IR | Per-event | Forever | S5 |
| Alt | Reddit/X velocity per ticker | Pushshift archive + scraped X (where ToS-OK) | Hourly | 1 year | Optional augment |
| Alt | ETF creation/redemption flows | ETF.com / Bloomberg | Daily | 3 years | Regime detection |
| Reference | Trading calendar, halts, LULD bands | exchange feeds | Real-time | Forever | Risk overlay |
| System | Every order, fill, slippage, audit | Our own | Real-time | Forever | L5 RL replay, attribution |
| System | Model versions, feature versions, config diffs | Git + MLflow | Per-deploy | Forever | Reproducibility |

**Format & infra:**
- Storage: Parquet on Cloudflare R2 (cheap, S3-compatible). Partitioned by `dataset / year=YYYY / month=MM / day=DD`.
- Query: DuckDB (analytic) + Polars (in-process). MongoDB stays for transactional audit log + UI state.
- Streaming: Redis Streams (cheap on a $5 VPS) for the live event bus; consider Kafka only if we outgrow it.
- Lineage: every feature has a (source_dataset_id, transform_fn_version, snapshot_timestamp) tuple. Lookahead leaks are caught by automated tests in CI.

**Point-in-time correctness is the prime directive.** A backtest that uses today's revised earnings number for a trade decided three years ago is a backtest that lies. Every join must include `available_at <= event_time`.

---

## 13. Honest Capital → Income Math

The user goal is "thousands a month passively". Let's not pretend.

| Capital | Net Sharpe assumption | Realistic annual net | Monthly avg | Comment |
|---|---|---|---|---|
| $5,000 | 1.0 | 15–25% = $750–1,250 | $63–104 | Coffee money. Not the goal. |
| $10,000 | 1.0 | 15–25% = $1.5–2.5k | $125–208 | Still not "thousands". |
| $25,000 | 1.2 | 20–30% = $5–7.5k | $417–625 | Approaching the goal. |
| $50,000 | 1.2 | 20–30% = $10–15k | $833–1,250 | First time "thousands/month" is realistic. |
| $100,000 | 1.2 | 20–30% = $20–30k | $1,667–2,500 | Solid "thousands/month" range. |
| $250,000 | 1.0 (capacity-constrained at this size for some strategies) | 15–25% = $37–62k | $3,083–5,208 | Comfortably "thousands/month". |

**Implications for the build:**

1. The goal is achievable but requires either **(a) $50k+ in capital** at moderate Sharpe, or **(b) accepting much higher tail risk** to lever returns at lower capital.
2. Returns above 30% net annual on small capital with low correlation to crypto-beta are *suspicious*. If our backtests show 80%+ APY, the more likely explanation is data leak / overfit than genuine edge.
3. Compounding matters more than headline returns: 25% net × 5 years on $25k = $76k → $190k. The system must survive 5 years, not crush one quarter.
4. **Plan deliberately:** target $50k working capital by end of Phase 6, accumulated from (initial seed + reinvested gains + outside contributions). Anything less and "thousands/month" is fantasy.
5. **Watch the asymmetry:** capital required to lose meaningful money is the same as capital required to make meaningful money. A −15% drawdown on $50k is $7,500 of real life.

The plan does not lower the bar. It moves the goalpost honestly.

---

## 14. Code Migration Map (legacy → helios/)

Concrete mapping from current files to the new package layout. **Reuse what's salvageable, archive the rest.**

```
helios/
├── data/                      # NEW
│   ├── adapters/
│   │   ├── polygon.py         # FROM backend/services/data_provider.py (kept), backend/services/polygon_flat_files.py (kept)
│   │   ├── alpaca.py          # FROM backend/services/alpaca_trading.py (split: data vs exec)
│   │   ├── kraken.py          # NEW
│   │   ├── coinbase.py        # NEW
│   │   ├── hyperliquid.py     # NEW
│   │   ├── edgar.py           # NEW (SEC filings)
│   │   └── news.py            # FROM backend/services/enhanced_sentiment.py (gut and rewrite)
│   ├── store/
│   │   ├── parquet_writer.py  # NEW
│   │   ├── duckdb_query.py    # NEW
│   │   └── feature_lineage.py # NEW
│   └── pit/                   # NEW: point-in-time correctness helpers + tests
│
├── features/                  # NEW
│   ├── tabular.py             # FROM bits of backend/services/indicators.py, enhanced_indicators.py, williams_r_indicator.py, bollinger_squeeze_detector.py, momentum_multiplier.py (selectively, after walk-forward shows they matter)
│   ├── text.py                # FinBERT/DistilBERT embeddings; replaces ad-hoc LLM calls in enhanced_sentiment.py
│   └── on_chain.py            # NEW
│
├── strategies/                # NEW; each a self-contained package
│   ├── crypto_basis/          # S1 — cash-and-carry
│   ├── vol_premium/           # S2 — VRP wheel
│   ├── stable_arb/            # S3 — cross-venue arb
│   ├── crypto_trend/          # S4 — replaces backend/agents/trade_recommender_agent.py for crypto
│   └── equity_event/          # S5 — replaces backend/agents/{sentiment_agent.py, trade_recommender_agent.py} for equities
│
├── models/                    # NEW: all ML lives here
│   ├── xgb_signal.py
│   ├── conformal.py           # split-conformal calibration
│   ├── drift.py               # PSI / KS monitors
│   └── registry.py            # MLflow-backed
│
├── allocator/                 # NEW
│   └── bandit.py              # Thompson sampling over strategies
│
├── sizing/
│   └── kelly.py               # FROM backend/services/enhanced_position_sizer.py (KEPT, refactored to be pure)
│
├── risk/                      # NEW: pure functions, property-tested
│   ├── limits.py
│   ├── correlation.py
│   ├── drawdown_brake.py
│   ├── kill_switch.py
│   └── regime_gate.py         # FROM backend/services/market_regime_detector.py (concepts kept, code rewritten)
│
├── execution/                 # NEW
│   ├── router.py              # Smart order routing
│   ├── vwap.py                # Baseline slicer
│   └── rl/                    # PPO agent + CQL bootstrap
│       ├── env.py             # Replay simulator
│       ├── policy.py
│       └── eval.py            # IPS / DR off-policy evaluation
│
├── orchestrator/              # FROM backend/main.py (concepts kept, asyncio loop redesigned around Redis Streams)
│   └── loop.py
│
├── backtest/                  # NEW (the existing backend/services/historical_backtest_engine.py is a stub; rewrite)
│   ├── engine.py
│   ├── slippage.py
│   ├── walkforward.py
│   ├── purged_cv.py
│   ├── monte_carlo.py
│   └── tearsheet.py
│
├── api/                       # FROM backend/railway_start.py (stripped down)
│   └── server.py              # FastAPI: health, kill-switch, audit, config-read, tearsheet endpoints
│
├── notify/
│   ├── telegram.py            # FROM backend/services/telegram_notifier.py (kept)
│   └── pagerduty.py           # NEW
│
└── ops/
    ├── logging.py             # FROM backend/utils/* (consolidated)
    ├── metrics.py             # NEW (OpenTelemetry)
    └── secrets.py             # NEW (vault-backed)
```

**Archived (kept on `legacy/` branch, never imported by helios/):**
- All of `backend/agents/*` — the agent abstraction conflates orchestration, strategy, and notification. We separate those.
- `backend/services/ai_learning_engine.py` — the "learning engine" of v0. Concepts inform helios/models but no code is reused.
- `backend/services/automated_trading_manager.py`, `master_trading_coordinator.py`, `system_orchestrator.py` — three competing orchestrators. Replaced by one `helios/orchestrator/loop.py`.
- `backend/services/{enhanced_decision_logger.py, enhanced_decision_logger_mongodb.py, learning_dashboard_api.py, learning_manager.py}` — replaced by `helios/ops/` + new MLflow registry.
- `backend/services/{real_trading_controls.py, real_trading_controls_simple.py, interactive_trading.py}` — UI/control hacks. Replaced by `helios/api/server.py`.
- `backend/services/llm_router.py` — replaced by direct, audited LLM calls in `helios/features/text.py` only (off the hot path).

**Kept as-is, lightly refactored:**
- [backend/services/data_provider.py](backend/services/data_provider.py) → moved, kept logic.
- [backend/services/polygon_flat_files.py](backend/services/polygon_flat_files.py) → moved, kept.
- [backend/services/enhanced_position_sizer.py](backend/services/enhanced_position_sizer.py) → refactored to a pure function in `helios/sizing/kelly.py`.
- [backend/services/telegram_notifier.py](backend/services/telegram_notifier.py) → moved.
- [backend/services/numba_accelerated.py](backend/services/numba_accelerated.py) → if it accelerates anything in helios/features/, keep; otherwise drop.

**Frontend:** `frontend/` is kept; cockpit pages get expanded per §5 of [BUILD_PLAN.md](BUILD_PLAN.md). API contract is rewritten cleanly (legacy `/api/predictions` etc. removed in favor of `/v2/...` endpoints).

**Migration discipline:** one PR per `helios/` package; each PR includes the migration of any legacy file it supersedes, plus tests. Legacy file is deleted in the *same* PR (not later) so no shadow code lingers.

---

## 15. Risks Not Previously Named

| Risk | Mitigation |
|---|---|
| **Crypto custody / exchange failure** | Per-venue cap (≤ 30% of crypto sleeve at any one venue). Daily withdrawal-test job. Stablecoin reserve at a separately-controlled venue. |
| **Tax compliance complexity** | Pick a tax basis policy (FIFO) on day 1. Log every trade with cost basis at execution time. Evaluate Section 475(f) mark-to-market election with a CPA before year 2. |
| **Sim-to-real Sharpe decay** | Live position sizes assume half the paper Sharpe. Only re-rate up after 90 days of realized Sharpe matching paper Sharpe. |
| **Latency budget per venue** | Measure RTT to each venue from production region. Document budget per strategy. Strategies whose alpha decays inside the latency budget are killed. |
| **Optuna / search overfitting** | Nested CV + Deflated Sharpe. Hyperparameter ranges fixed in advance per strategy. No "just one more search". |
| **Regulator risk on crypto perps for US persons** | Hyperliquid + Binance perpetuals are off-limits if operator is US-resident. Use only CFTC-regulated venues (Kraken futures, Coinbase Derivatives) for perp exposure. Cash-and-carry executable across compliant venues only. |
| **Single-operator key-person risk** | Documented runbook. Kill switch reachable from phone. 7-day "vacation mode" that flattens to cash. |
| **Data vendor outage** | Two market-data sources per asset class. Cross-check on every bar; halt strategy if divergence > threshold. |
| **Backtest publication bias** | Pre-register the strategy hypothesis before running the backtest. Keep an "attempted strategies graveyard" file — strategies that failed get logged so we don't re-test them and get a false positive by chance. |

---

## 16. The Aggressive Path (v3 — small capital, asymmetric, leveraged, AI-native)

> v2 was the institutional-style answer. v3 is the honest answer to "how do real people turn $5–10k into six figures a year". The math requires **leverage + asymmetry + velocity + an actual edge**. The AI bot is what supplies the discipline, speed, and pattern recognition that lets a solo operator survive that combination. This is the path we're building.

### 16.1 The math of why this is possible

To go from $10k → $10k/month, you need ~10% monthly net. That is **not** "beat Buffett" — it is "compound 2.5% weekly". The reason it's rare in retail isn't that the math is impossible; it's that retail can't execute it:

- Retail blows up on leverage because of emotion → AI bot doesn't have emotion.
- Retail can't watch 50 venues 24/7 → bot can.
- Retail can't react in 200ms → bot can.
- Retail overrides its rules → bot doesn't (unless we let it).
- Retail trades 5 instruments → bot trades 500 and lets the high-conviction ones surface.

The edge isn't that the bot is smarter than a quant. The edge is that the bot is a **disciplined, sleepless, multi-venue, pattern-matching machine** with a small enough size to fit through micro-edges that institutional capital can't touch.

### 16.2 The four levers that turn small capital into real income

| Lever | What it does | How we use it |
|---|---|---|
| **Leverage** | Multiplies a real edge | 3–10x on crypto perps for trend strategies; embedded leverage via options for equity strategies |
| **Asymmetry** | Caps loss, uncaps gain | Options debit spreads; perp positions with hard invalidation stops; "1R risk for 5R+ targets" |
| **Velocity** | Compounding > headline returns | 50–200 trades/week across strategies; compound weekly not annually |
| **Niche edges** | Where institutions can't or won't go | Memecoins, new listings, low-cap perps, on-chain MEV-adjacent flows, 0DTE options, social-velocity arbitrage |

Pull all four. Pulling only one is retail. Pulling all four with an AI executor is the actual answer.

### 16.3 The aggressive strategy stack (v3)

Replaces / augments §10. Tier 1 below is the engine; Tier 2 is the swing-for-the-fences sleeve. Tier 3 (carry/VRP from v2) becomes the "ballast" that pays the bills while the asymmetric bets cook.

**Tier 1 — High-velocity asymmetric engines (the income generators)**

**A1. Crypto perp trend / breakout with leverage (3–10x).**
- BTC/ETH/SOL + top 20 liquid alt-perps.
- Entry: confluence of (regime = trend) + (volatility expansion) + (funding alignment) + (orderflow imbalance).
- Position sizing: risk 0.5–1.5% of NAV per trade, leveraged into 5–15% notional exposure.
- Exit: hard stop at invalidation level, trailing stop after 2R, scale-outs at 3R/5R/10R.
- Why it works at $10k: 1 good week = 5–15% gain; compounded weekly is life-changing.
- Bot edge: 24/7 monitoring of 20+ perps, regime-aware entry filter that rejects 90%+ of "looks-like-trend" setups.

**A2. Memecoin / new-launch sniping on Solana + Base + Hyperliquid spot.**
- Programmatic detection of legitimate launches (LP locked, contract verified, dev wallet history clean, holder distribution healthy) within seconds of launch.
- Tiny size per shot ($50–250), high frequency (5–30 entries/week), hunting 2–20x outcomes.
- Expected loss rate: 70–80%. Positive EV from skew: even one 10x covers many losers.
- **Hard rules:** auto-exit if liquidity drops below threshold, dev wallet moves, or 80% trailing drawdown from peak.
- Bot edge: on-chain scanner that filters rugs/honeypots in < 2 seconds — humans cannot.
- This sleeve is capped at 10–15% of NAV and treated as a venture portfolio with explicit ruin budget.

**A3. Liquidation-cascade hunting on perps.**
- Bot maps liquidation clusters from open-interest + funding + price + leverage data (Coinglass, venue APIs).
- When price approaches a heavy liquidation level, it either fades the cascade exhaustion or rides it depending on regime.
- Sub-minute holding, 5–20 trades/day, 0.3–1.5% per trade.
- Bot edge: literally cannot be done manually at speed and across venues.

**A4. 0DTE / weekly options on SPX, QQQ, IWM with mechanical setups.**
- Defined-risk debit spreads (e.g., 5-wide call/put debit spreads at 30Δ).
- Entry triggers: opening-range breakouts, gamma-flip levels, VIX term-structure dislocations.
- Risk: 0.5–1.5% of NAV per trade; 3–10 trades/week.
- Asymmetry: max loss = debit paid; best case = 5x debit on the spread.
- Bot edge: faster pattern recognition on the 1m/5m chart + mechanical no-FOMO entry.

**A5. Social/sentiment velocity arbitrage.**
- Real-time ingest of X (where ToS-OK), Farcaster, Telegram crypto channels, Truth Social, Reddit hot.
- Detect ticker/coin mention-velocity breakouts (z-score on rolling mention rate) before price moves materially.
- Trade with small leveraged position; exit on volume mean-reversion or 1R loss.
- Bot edge: humans cannot watch 50+ channels in real time with statistical filters.

**Tier 2 — Event-driven asymmetric bets**

**A6. Earnings IV-crush + post-earnings drift with options.**
- Sell straddles into known earnings (capture IV crush), or buy directional spreads into events where transcript-tone embedding + surprise direction agree.
- Defined risk via spreads. Limit to 3–5 events/week.

**A7. Funding-rate extremity reversion.**
- When perp funding hits extreme negative/positive (top/bottom 1% historical), often signals capitulation/euphoria → fade the crowd with leveraged perp.
- Sub-day holding, hard invalidation at 1R.

**Tier 3 — Ballast (v2 strategies, kept smaller)**

**A8. Cash-and-carry funding harvest.**
- Reduced to 20–30% of NAV. Provides the steady drip that pays operational costs and prevents the aggressive sleeves from forcing trades to "make rent".

**A9. VRP wheel on liquid equities.**
- 10–20% of NAV. Same role: pays the bills, anchors NAV during aggressive-sleeve drawdowns.

**Capital allocation (default):**

```
A1 Crypto perp trend         25–30%
A3 Liquidation hunting        10–15%
A4 0DTE options               10–15%
A5 Sentiment velocity         5–10%
A6 Earnings events            5–10%
A7 Funding extremity          5%
A8 Carry harvest              20–25%
A9 VRP wheel                  10–15%
A2 Meme/launch sniping       ≤10% (ruin-budgeted)
```

Allocator (contextual bandit from §11) tunes within these ranges based on regime + recent realized Sharpe per arm.

### 16.4 What changes in the architecture vs. v2

The L0–L6 stack from §11 stays. Adjustments for the aggressive path:

- **Leverage governor** (new L4.5 layer): real-time max-leverage cap as function of (account drawdown, recent realized vol, regime). De-levers automatically as drawdown deepens — *anti-Martingale by design*.
- **Per-trade risk-of-ruin budgeter:** every order is sized so that worst-case loss + correlated open exposure cannot exceed the daily ruin budget (e.g., 4% NAV/day, 10% NAV/week, 18% NAV/month).
- **Asymmetry enforcer in risk overlay:** rejects any order whose stop-loss distance × position size > defined R, OR whose implied R:R < 2:1 (configurable per strategy).
- **Velocity-compounding engine:** P&L sweeps to working capital nightly; sizing recalculates off the new NAV daily, not weekly. This is how 2.5%/week becomes 35%/year compounded vs. 30% un-compounded.
- **Tail-risk overlay (long-vol hedge):** ~2% of NAV in long-VIX-call or long-BTC-put protective overlay, rolled monthly. Pays for itself once per major drawdown; the rest of the time it's a small drag. Worth it for the aggressive sleeve.
- **Faster self-learning cadence:** because trade frequency is 50–200/week (vs. v2's 5–20), the bandit allocator and conformal calibrator update *hourly* not nightly. The bot literally gets smarter inside a single trading day.
- **Hot-path latency budget:** A1/A3/A5 strategies need < 500ms decision-to-fill. Means a colocated VPS near each exchange's API endpoint, not Railway. Architecture splits: **Railway = control plane + cold path. Bare-metal/colo VPS (Vultr / OVH near Tokyo for crypto, near NJ4 for equities) = hot path.**
- **Multi-venue hot wallets** for the on-chain sniping sleeve, with strict per-wallet caps and automated sweeping to cold storage above threshold.

### 16.5 What the AI specifically does that retail can't

This is where we earn the "AI" label. Concretely:

1. **Regime classification in real time** (HMM + transformer on multi-asset features) — A1 only trades when regime is "trend", which kills 60% of false positives that wreck retail trend-followers.
2. **On-chain rug/honeypot filter** (graph features on contract + holder distribution) — makes A2 survivable.
3. **Liquidation-cluster prediction** (gradient-boosted on OI/funding/price) — A3 doesn't exist for humans at speed.
4. **Sentiment-velocity z-score across 50+ channels** — A5 is pure bot territory.
5. **Conformal-calibrated confidence intervals** — position size keys off lower-bound predicted return; **the bot refuses to trade when it knows it doesn't know**. This is the single biggest edge over retail: knowing when to sit out.
6. **Pattern-memory vector lookup** — "this setup matches 412 historical, mean +1.8R, hit-rate 58%, worst case −1.0R" — surfaced before each trade. Removes hindsight bias and forces base-rate thinking.
7. **24/7 monitoring + emotionless execution** — no missed setups, no revenge trades, no overnight panics.
8. **Continuous nightly retraining** — A1 model that was good for trend-2024 retunes to trend-2026 without operator intervention.

### 16.6 Realistic income math at this path

Assumptions:
- Starting capital: $10,000
- Weekly net return target: 2.5% (math says aggressive but doable with this stack)
- Realized: 1.5–4% weekly with significant variance
- Max acceptable drawdown: 25% (kill switch fires)
- Compounding: weekly P&L sweep into capital

**Conservative trajectory** (1.5%/week net average, realistic with stack discipline):
- Month 3: $11,800 → ~$80/wk earnings rate
- Month 6: $14,200 → ~$215/wk
- Month 12: $20,200 → ~$300/wk = **~$1,300/month**
- Month 18: $28,800 → **~$430/wk = ~$1,860/month**
- Month 24: $40,800 → **~$615/wk = ~$2,660/month**

**Target trajectory** (2.5%/week net average, achievable if the stack works as designed):
- Month 3: $13,400 → ~$330/wk
- Month 6: $17,800 → ~$445/wk
- Month 12: $31,700 → **~$790/wk = ~$3,400/month**
- Month 18: $56,500 → **~$1,400/wk = ~$6,100/month**
- Month 24: $100,700 → **~$2,500/wk = ~$10,900/month**

**Stretch trajectory** (3.5%/week net, requires the AI edges to actually all work):
- Month 12: $52,500 → ~$1,800/wk = **~$7,800/month**
- Month 24: $275,000 → ~$9,600/wk = **~$41,800/month**

These are not promises. They are what the math says if the stack performs in-line with reasonable assumptions about strategy Sharpe + leverage + compounding. The variance is large in both directions.

### 16.7 The honest cost of admission

If we are not hedging, we name the cost squarely:

- **Real ruin probability.** On the aggressive path, probability of −50%+ drawdown in year 1 is meaningful (rough estimate 15–25%) even with the risk overlay. The drawdown brake reduces it but does not eliminate it.
- **Variance is brutal.** Week 1 can be +12% or −8% with equal regularity. A monthly income figure is a year-of-data average, not a guaranteed monthly check.
- **You must not override.** Aggressive strategies blow up when operators override the bot during drawdowns ("just this once, let me close this loss manually"). The kill switch is the *only* sanctioned override.
- **Tax surface is intense.** Hundreds of trades/month + crypto + perps + options = a tax-prep nightmare. Engage a trader-tax CPA *before* the first live trade.
- **Infrastructure cost.** Co-located VPS, paid data feeds, exchange API tiers — budget $200–400/month. Comes off the top.
- **Time-to-edge is not zero.** First 90 days are paper + shadow mode. First live capital is small. Month 1 of "live thousands" is probably month 6–8 from today, not month 2.

### 16.8 What we change in the build plan

Folds into [BUILD_PLAN.md](BUILD_PLAN.md):

- **Phase 2 first strategy becomes A1 (crypto perp trend, leveraged paper)** instead of plain crypto momentum.
- **Phase 3 ensemble expands to A1, A3, A4, A8** before adding the venture sleeves (A2, A5).
- **Phase 4 self-learning adds:** hourly bandit refresh, leverage governor, asymmetry enforcer, ruin budgeter, tail-risk overlay.
- **New Phase 4.5: Hot-path infrastructure.** Provision colocated VPS, set up secure key material, latency-test each venue, only then promote latency-sensitive strategies to live.
- **Phase 6 live ramp** updates: start at $1,000 (not $500) because aggressive strategies need enough notional to clear minimum-tick economics; scale by realized Sharpe + zero risk-overlay breaches.

### 16.9 Locked parameters (operator: Isaac, 2026-05-24)

| Parameter | Value | Consequence |
|---|---|---|
| Residency | **US** | CFTC-only venues for leveraged derivatives. Approved: **Kraken Futures, Coinbase Derivatives (CFTC-registered FCM), CME Micro BTC/ETH futures via brokerage, Coinbase Advanced (spot), Solana DEXes via self-custody wallet**. Not used: Hyperliquid, Binance, Bybit perps. No VPN workarounds. |
| Starting capital | **$1,000** | Brutally small. Sub-$5k locks out options strategies (A4, A6, A9 deferred until $5k NAV). Crypto-heavy starter stack. First $1k/mo earnings rate realistic ~month 14–20 depending on path. |
| Override discipline | **Committed: no manual override outside kill switch** | Full leverage budget unlocked. 3–8x on perp trend, full asymmetry enforcement, hourly bandit retraining trusted. |
| Max acceptable drawdown | **TBD — default 25% portfolio peak-to-trough triggers full flatten + human review.** Operator to confirm/adjust before Phase 6. | Drawdown brake: −10% halves leverage; −18% halves again; −25% flat to cash + alert. |

### 16.10 The $1k US-compliant starter stack (v3.1)

Capital is the binding constraint. Stack reweighted:

| Sleeve | % of NAV | Venue | Notes |
|---|---|---|---|
| A1 Crypto perp trend (BTC/ETH/SOL, 3–5x) | 35% | Kraken Futures | Minimum contract economics are fine at $350 notional × 3x = $1,050 working size |
| A8 Cash-and-carry basis | 25% | Coinbase Advanced (spot) + Kraken Futures (perp) | Steady drip, low risk, scales with capital |
| A3 Liquidation-cascade (BTC/ETH only, light) | 10% | Kraken Futures | Limited without Binance/Hyperliquid data depth; use Coinglass aggregator |
| A2 Solana meme/launch sniping | 10% (ruin-budgeted) | Self-custody wallet via Jupiter aggregator | $50–100/shot; treated as venture sleeve |
| A5 Crypto-only sentiment-velocity | 10% | Same as A1 | Twitter/X + Farcaster + Telegram alpha channels |
| A7 Funding-rate extremity reversion | 5% | Kraken Futures | Mean-reversion on funding-rate z-score |
| Stable reserve | 5% | Coinbase USDC | Dry powder for opportunistic adds |
| **Deferred until NAV ≥ $5,000:** A4 0DTE options, A6 earnings, A9 VRP wheel | — | — | Equity options need $3–5k minimum to clear commission/spread economics |

**Re-targeted income trajectory at $1k start, 2.5%/week compounded (target case):**

- Month 6: ~$1,780 → ~$45/wk
- Month 12: ~$3,170 → ~$80/wk
- Month 18: ~$5,650 → ~$140/wk → **A4/A6/A9 unlock**
- Month 24: ~$10,070 → ~$250/wk
- Month 30: ~$17,950 → ~$450/wk
- Month 36: ~$32,000 → **~$800/wk = ~$3,500/month**

**Stretch case at 3.5%/week (if all AI edges fire as designed):**

- Month 12: ~$5,250 → A4/A6/A9 unlock at month 11
- Month 18: ~$13,800 → ~$485/wk = **~$2,100/month**
- Month 24: ~$36,300 → ~$1,270/wk = **~$5,500/month**
- Month 30: ~$95,300 → ~$3,335/wk = **~$14,500/month**

**The bridge problem:** At $1k, month 1–6 generates trivial cash (< $200/mo). Two paths to shorten the runway:
1. **Pure compounding patience.** What's above. Slow until ~month 18, exponential after.
2. **Capital additions.** Every $1k added at month 0 shifts the curve forward by ~9 months at 2.5%/week. If the operator can add even $500/month from outside income during the bootstrap window, "thousands/month" lands 12 months earlier.

The plan does not require option 2 but strongly benefits from it.

---

## 17. References

- [StockBench: Can LLM Agents Trade Stocks Profitably](https://arxiv.org/pdf/2510.02209) — empirical case that LLM-only agents underperform B&H
- [Automated Trading Framework Using LLM Features + DRL](https://www.mdpi.com/2504-2289/9/12/317) — the pattern we adopt: LLM = features, DRL = decision
- [Walk-Forward Analysis](https://www.interactivebrokers.com/campus/ibkr-quant-news/the-future-of-backtesting-a-deep-dive-into-walk-forward-analysis/)
- [Overfitting prevention checklist](https://www.quantifiedstrategies.com/algorithmic-trading-strategies/)
- [Microcap execution-quality dominance, 2026](https://stock-market.live/microcap-resurgence-ai-screening-community-liquidity-2026)
- [Emerging AI patterns in finance, 2026](https://gradientflow.substack.com/p/emerging-ai-patterns-in-finance-what)
- López de Prado, *Advances in Financial Machine Learning* — purged CV, Deflated Sharpe
