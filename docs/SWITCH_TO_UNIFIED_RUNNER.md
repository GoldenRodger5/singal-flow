# Switch Railway to the unified runner (one service, all strategies)

The existing Railway service runs only A2 shadow mode. With the new unified
runner you get **all 4 strategies in one process** — same volume, same logs,
~$5/month total instead of ~$20/month for 4 services.

## Trade-offs

|  | One service (recommended) | Four services |
|---|---|---|
| Monthly base cost | ~$5 | ~$20 |
| Volumes to manage | 1 | 4 (or shared mount — finicky) |
| Logs | all in one `/data/logs` | scattered, harder to query together |
| Crash isolation | per-task supervisor restarts the bad strategy; the rest keep running | service-level isolation (true OS-level) |
| Deploy churn | one redeploy updates everything | each service redeploys on every push |
| Capacity at scale | fine for shadow + paper; if you ever go LIVE on multiple strategies with high frequency you'd split later | over-provisioned today |

For shadow-mode + paper-mode data collection, **one service is unambiguously the right answer.** Split into separate services later if/when a single strategy outgrows it.

## How to switch (60 seconds)

1. Open the Railway dashboard for `tender-tenderness`.
2. Click the **service tile** (the green "Online" one) → **Settings** tab.
3. Scroll to the **Deploy** section. Find **"Custom Start Command"** (or "Service Start Command" depending on Railway's current UI naming).
4. Set it to:
   ```
   python -m scripts.helios_all
   ```
5. Click **Save** at the bottom.

Railway redeploys automatically. The new container boots with **all 4 strategies running in parallel** under the task supervisor.

## What you'll see in the logs

```
======================================================================
Helios unified runner — all enabled strategies in one process
  A2 shadow:  ON
  A2 live:    ON (paper-mode)
  A3 shadow:  ON
  A5 shadow:  ON
  Live safety: paper-mode (default)
======================================================================
2026-05-25 ... INFO supervisor_starting n_tasks=4 names=['a2_shadow', 'a2_live', 'a3_shadow', 'a5_shadow']
2026-05-25 ... INFO supervised_task_starting name=a2_shadow
2026-05-25 ... INFO supervised_task_starting name=a2_live
2026-05-25 ... INFO supervised_task_starting name=a3_shadow
2026-05-25 ... INFO supervised_task_starting name=a5_shadow

[2026-05-25T...] iter=   1 shadow ok ...      ← A2 shadow first iteration
2026-05-25 ... INFO a2_live_runner_starting   ← A2 live ready (paper-mode)
2026-05-25 ... INFO a3_shadow_starting        ← A3 ready
2026-05-25 ... INFO a5_shadow_starting        ← A5 ready
```

Then logs from all four strategies interleave forever. Each strategy writes to its own JSONL file in `/data/logs/`:

| File | Strategy |
|---|---|
| `a2_shadow.jsonl` | A2 shadow observations |
| `a2_outcomes.jsonl` | A2 outcomes harvested 24h after detection |
| `a2_live_fills.jsonl` | A2 live-paper fills |
| `a3_shadow.jsonl` | A3 cascade signals |
| `a5_shadow.jsonl` | A5 sentiment signals |
| `pattern_memory.jsonl` | Vector memory of closed trades |
| `llm_token_scores.jsonl` | Claude scoring cache |
| `helios.jsonl` | Structured audit log |

## If a task crashes

The supervisor catches the exception, logs it, and restarts that one task with exponential backoff (1s → 2s → 4s → ... capped at 5 min). The other 3 tasks keep running undisturbed.

Look for log lines like:
```
[supervisor] task 'a5_shadow' crashed after 247s — restart in 1s
Traceback (most recent call last):
  ...
2026-05-25 ... INFO supervised_task_starting name=a5_shadow
```

If a task crashes repeatedly (>3 consecutive crashes within 5 min each), inspect the trace — there's a real bug, not a transient issue.

## Optional env vars to unlock more

| Var | What it unlocks |
|---|---|
| `X_API_BEARER` | A5 reads X mentions (free tier: ~100 reads/month — limited) |
| `NEYNAR_API_KEY` | A5 uses Neynar's trending Farcaster feed instead of public Warpcast |
| `COINGLASS_API_KEY` | A3 reads the liquidation-level heatmap (premium-tier endpoint) |
| `GITHUB_TOKEN` + `GITHUB_REPO` | Periodic JSONL backup to a `data-snapshots` branch |
| `SAFETY_LIVE_TRADING=I_UNDERSTAND_THE_RISK` | A2 live can submit real swap transactions (DO NOT SET until shadow proves edge) |
| `SOLANA_PRIVATE_KEY` (base58) | Wallet to sign with when live mode is enabled |

## Rollback (if anything goes wrong)

Same Settings → Custom Start Command field. Change back to:
```
python -m scripts.a2_run_continuous
```
Save → Railway redeploys with just the original A2 shadow runner.

## Summary

- **3 separate services → 1 unified service.** Cheaper, simpler, consolidated logs.
- **Per-task supervisor** keeps the system alive through individual-strategy bugs.
- **One config change** in Railway dashboard → 4 strategies running in parallel.

Decision Point #1 (Jun 1) will now have data from **all 4 strategies** instead of just A2. That's the whole point.
