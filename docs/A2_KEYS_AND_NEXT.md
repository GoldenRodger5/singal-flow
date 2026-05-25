# A2 — what's built, what's needed next

## What's shipped (A2.1)

- **`helios/strategies/a2_meme_snipe/snapshot.py`** — `TokenSnapshot` dataclass; immutable point-in-time view of a Solana token + its pool.
- **`helios/strategies/a2_meme_snipe/rug_filter.py`** — `RugFilter`: 5-bucket check battery (K authorities, L liquidity, C concentration, P provenance, M microstructure). Pure logic, deterministic. **17 tests, all green.**
- **`helios/strategies/a2_meme_snipe/strategy.py`** — `A2MemeSnipe`: Strategy ABC implementation, queue-based candidate intake, emits `Signal` only on filter pass.
- **`helios/data/adapters/dexscreener.py`** — public, no-auth DexScreener snapshot adapter (fills L + M fields).
- **`scripts/a2_shadow_mode.py`** — runner skeleton.

## Safety-by-default property (verified by test)

A `TokenSnapshot` with default / unknown fields **REJECTS**, never passes. Adapters that fail to fill authority or holder data cannot accidentally let a rug through. See [test_default_unknown_snapshot_rejects](../tests/helios/strategies/test_rug_filter.py).

## What A2.2 needs from the operator (you)

### Minimal — to unlock live detection + filter

| Key | Tier | What it provides | Where |
|---|---|---|---|
| `HELIUS_API_KEY` | Free (100k credits/day) | Solana RPC; new-pool detection via `getProgramAccounts` on Raydium/Pump.fun; LP authority checks; mint/freeze authority reads | https://www.helius.dev |
| `BIRDEYE_API_KEY` | Free tier | Top-10 holder concentration; historical pricing for backtest replay; token metadata | https://docs.birdeye.so |

Both have free tiers sufficient for shadow-mode logging at $1k notional. Sign up takes ~2 minutes each. Keys go in [.env](../.env) (which is `.gitignore`d).

### Optional later — for live execution (A2.4)

| Key | When | What it provides |
|---|---|---|
| `SOLANA_HOT_WALLET_KEY` | A2.4 only | Self-custody wallet private key for Jupiter swap execution. **Do not provision until A2.3 paper-mode shows positive net-of-friction P&L.** |
| `JITO_TIP_ACCOUNT` | A2.4 only | MEV-protection bundle submission (optional but reduces sandwich attacks) |

## What A2.2 will be when keys arrive

1. **`helios/data/adapters/helius.py`** — websocket subscription to new-pool events on Raydium + pump.fun → pushes mint addresses into a detection queue.
2. **`helios/data/adapters/birdeye.py`** — given a mint, fills the authority + holder + dev-history fields of `TokenSnapshot` that DexScreener doesn't provide.
3. **`scripts/a2_shadow_mode.py` upgraded** — runs continuously. On each detected new pool: build full snapshot, run filter, log decision. Every 24 hours: pull post-launch price action for each logged "would-have-bought" and compute realized P&L distribution.
4. **`logs/a2_shadow.jsonl`** — append-only audit log. After 7–14 days of shadow runs, we have empirical filter performance data. **This is the gate to A2.3.**

## Calibration plan after shadow data arrives

Once we have ~200 filtered candidates with measured 24-hour post-decision P&L:

1. Compute win rate (P&L > 0), median return, max drawdown distribution.
2. Compute the **single most binding filter check** (which rejection code, if relaxed by 1 std, would have caught the most missed winners without catching too many extra rugs).
3. Bayesian update on filter thresholds with held-out validation.
4. Only if 7-day median return > 0 (after estimated 15% round-trip slippage) → graduate to A2.4 paper-execution.

## Running the continuous shadow collector

`scripts/a2_run_continuous.py` is the data-collection loop. Pick one deployment:

### Option A — tmux (recommended for the first few days)
```bash
tmux new -s a2-helios
python -m scripts.a2_run_continuous
# detach with Ctrl-b d ; reattach with: tmux attach -t a2-helios
```

### Option B — nohup background
```bash
mkdir -p logs
nohup python -m scripts.a2_run_continuous > logs/a2_continuous.out 2>&1 &
echo $! > logs/a2_continuous.pid
# stop later: kill $(cat logs/a2_continuous.pid)
# watch progress: tail -f logs/a2_continuous.out
```

### Option C — macOS launchd (auto-start on login)

Create `~/Library/LaunchAgents/com.helios.a2.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.helios.a2</string>
  <key>WorkingDirectory</key><string>/Users/isaacmineo/Main/projects/singal-flow</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>-m</string><string>scripts.a2_run_continuous</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/isaacmineo/Main/projects/singal-flow/logs/a2_continuous.out</string>
  <key>StandardErrorPath</key><string>/Users/isaacmineo/Main/projects/singal-flow/logs/a2_continuous.err</string>
</dict>
</plist>
```

Then: `launchctl load ~/Library/LaunchAgents/com.helios.a2.plist`
Stop: `launchctl unload ~/Library/LaunchAgents/com.helios.a2.plist`

### Useful flags

```bash
# Faster intervals if you want denser data (eats more Birdeye credits):
python -m scripts.a2_run_continuous --shadow-interval-min 15 --shadow-limit 30

# Strict P02 (no data will pass filter until dev-history indexer is built):
python -m scripts.a2_run_continuous --no-relax-p02

# Test one iteration end-to-end:
python -m scripts.a2_run_continuous --max-iterations 1
```

### Monitoring what's collected
```bash
# How many observations and outcomes do we have?
wc -l logs/a2_shadow.jsonl logs/a2_outcomes.jsonl

# Read the current outcome summary without harvesting again:
python -m scripts.a2_outcomes --summary
```

## Honest expected outcome

The most likely shadow-mode result is one of:

- **Filter is too strict**: 200 candidates detected, 5 pass, 1 winner, 4 zeros. Need to relax to find more setups.
- **Filter is too loose**: 200 candidates, 80 pass, win rate 8%, median return −60%. Need to tighten.
- **Filter is well-calibrated**: 200 candidates, 20 pass, win rate 15–20%, median return slightly positive after slippage, with a long right tail.

The third outcome is what we hope for. Either of the first two informs the next iteration in days, not months. The whole point of shadow mode is to learn fast at zero capital risk.
