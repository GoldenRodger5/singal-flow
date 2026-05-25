# GitHub backup of shadow-log data

The continuous runner can periodically push its JSONL data files to a separate
branch of your GitHub repo. This gives the data durability that Railway's
ephemeral container storage doesn't (and that the Volume feature would
otherwise provide). Restarts, redeploys, env-var changes — none of those
wipe your data anymore.

## Setup (one time, ~3 minutes)

### 1. Generate a fine-grained Personal Access Token

Go to https://github.com/settings/personal-access-tokens/new

- **Token name**: `helios-backup` (or whatever you like)
- **Expiration**: pick something reasonable. **90 days** is a good default; rotate when it expires.
- **Repository access**: **Only select repositories** → pick **`GoldenRodger5/singal-flow`** only. Do NOT grant access to all your repos.
- **Repository permissions**, scroll to:
  - **Contents**: **Read and write** ✓
  - Leave everything else as "No access"

Click **Generate token**. **Copy it immediately** — GitHub only shows it once.

### 2. Add it to Railway

In your Railway service settings → **Variables** tab → add two new variables:

| Key | Value |
|---|---|
| `GITHUB_TOKEN` | (paste the token you just generated) |
| `GITHUB_REPO` | `GoldenRodger5/singal-flow` |

Save. Railway redeploys the service automatically.

### 3. Verify it works

Within ~6 hours of the next deploy, look at the runtime logs. You should see a line like:

```
[2026-05-25T08:09:59+00:00] backup -> github  ok
```

And in GitHub, you'll see a new branch called `data-snapshots` with 1–3 files in it (`a2_shadow.jsonl`, `a2_outcomes.jsonl`, `a2_status.json`), updated every 6 hours.

## What's in the backup branch

- `a2_shadow.jsonl` — every shadow observation (filter input + decision)
- `a2_outcomes.jsonl` — every harvested outcome (post-detection price action)
- `a2_status.json` — current bot state (iteration count, totals, etc.)

That's it. **No code, no secrets, no `.env`.** Only the data the bot collected.

## Restoring on a fresh container

If Railway redeploys and wipes `/data/logs/`, the bot starts with empty files
— but the GitHub backup branch still has everything from the last cycle. To
restore (until we add an auto-restore feature):

```bash
# from your local machine, with the repo cloned:
git fetch origin data-snapshots
git checkout origin/data-snapshots -- a2_shadow.jsonl a2_outcomes.jsonl
# inspect locally with:
python -m scripts.a2_outcomes --summary
```

(Auto-restore on container start could be added in a future iteration — for
now backup-only is enough since the worst-case is ~6 hours of newly collected
data lost between backups.)

## Security notes

- Token scope is single-repo + Contents only. Lost token = attacker can push
  to your singal-flow repo's branches but cannot touch any other repo or
  account settings.
- Token is stored encrypted in Railway's variables system, never in code,
  never logged.
- Rotate when the expiration nears or if the token is ever exposed.
- To revoke: GitHub → Settings → Developer settings → Fine-grained PATs →
  click the token → Delete.

## Cost & limits

- **GitHub Contents API**: 5,000 req/hour for authenticated PATs. Our backup
  uses ~3 req per backup cycle (one per file). At default 6-hour cadence
  that's 12 req/day. Far under the limit.
- **GitHub storage**: free for repos under 100 GB. Our JSONL data won't reach
  even 100 MB for years.
- **Network egress from Railway**: negligible (a few KB per backup).

## What happens if backup fails

The bot logs the error and keeps running. A single failed backup doesn't stop
the shadow loop. Multiple consecutive failures will be visible in the runtime
logs — investigate then (most likely cause: expired token, revoked token, or
repo permissions changed).
