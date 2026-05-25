# A2 Collector Deployment — Pick One

You want a bot that runs 24/7 collecting Solana token launch data, surviving you closing your laptop. Three real options, ranked from easy-but-fragile to proper-autonomous.

## Honest reality check on the laptop

Your current Mac is configured for default sleep behavior. **Closing the lid puts the system to sleep. tmux sessions pause. Network connections drop. The collector freezes.** This is not a bug, it's how macOS works. There is no setting that makes "close lid, keep working" trivially safe on battery.

So pick one of the following based on how committed you are.

---

## Option A — Laptop stays open, plugged in (the lazy path)

**Use when**: you're testing for 1–2 days at a desk, machine is plugged in, you can leave it alone.

**Limitations**: must stay plugged in; lid must stay open; WiFi must stay on; sleeping the machine manually will pause it.

```bash
cd /Users/isaacmineo/Main/projects/singal-flow
./scripts/run_collector_macos.sh
```

That's literally it. The script wraps the runner with `caffeinate -dimsu` which tells macOS not to sleep system, display, idle, or disk while the process is alive.

To detach so you can close your terminal but keep the bot running, use tmux:

```bash
tmux new -s a2 './scripts/run_collector_macos.sh'
# Ctrl-b d to detach
# tmux attach -t a2 to come back
```

**Check progress without running any command:**
```bash
cat logs/a2_status.json
```
That file is rewritten every iteration with current state. No more invoking `a2_outcomes` just to see if it's alive.

---

## Option B — Railway cloud deploy (the right answer for "autonomous bot")

**Use when**: you want this to actually run 24/7, survive lid close, reboot, network outages, you closing your laptop and forgetting about it for a week.

**Cost**: Railway's hobby plan is ~$5/month with a $5 starting credit. The collector is tiny (idle most of the time) so monthly burn should be well under the credit at default cadence.

**One-time setup** (~10 minutes):

1. Install the Railway CLI:
   ```bash
   brew install railway   # or: npm i -g @railway/cli
   railway login
   ```

2. Initialize a new Railway project pointing at this repo:
   ```bash
   cd /Users/isaacmineo/Main/projects/singal-flow
   railway init                # accept defaults; pick "Empty service"
   railway link                # if not auto-linked
   ```

3. Tell Railway to use the Helios Dockerfile (not the legacy one):
   ```bash
   # In the Railway dashboard for this service → Settings → Build:
   #   Builder = Dockerfile
   #   Dockerfile Path = Dockerfile.helios
   ```

4. Add the secrets it needs at runtime:
   ```bash
   railway variables --set "HELIUS_API_KEY=<YOUR_HELIUS_KEY>"
   railway variables --set "BIRDEYE_API_KEY=<YOUR_BIRDEYE_KEY>"
   ```

5. Add a persistent volume so the JSONL logs don't vanish on redeploy:
   ```bash
   # Dashboard → Service → Settings → Volumes → New Volume
   #   Mount path: /data
   #   Size: 1 GB (way more than needed)
   ```

6. Deploy:
   ```bash
   railway up
   ```

That's it. The collector now runs in the cloud regardless of your laptop state. View logs with:
```bash
railway logs --tail
```

Or pull the status file via:
```bash
# (Railway doesn't expose volume files via CLI; easiest is to add a tiny HTTP
# endpoint that serves /data/logs/a2_status.json. Phase-2 nicety, not required.)
```

When you want to inspect outcomes, use Railway's CLI:
```bash
railway run python -m scripts.a2_outcomes --summary
```

---

## Option C — Cheap always-on VPS ($5/month, most control)

**Use when**: you'd rather own the box. Less convenient than Railway but cheaper if you scale up.

Recommended host: Hetzner CX11 (~$4.50/month, EU regions) or DigitalOcean Basic Droplet ($6/month).

```bash
# on a fresh Ubuntu 24.04 VPS as root or via ssh:
apt update && apt install -y python3 python3-pip git tmux
git clone <your-repo-url> /opt/helios
cd /opt/helios
pip3 install --break-system-packages \
  pydantic loguru anyio httpx orjson polars duckdb pyarrow \
  numpy pandas scipy scikit-learn xgboost python-dotenv

cat > /etc/systemd/system/helios-a2.service <<'EOF'
[Unit]
Description=Helios A2 collector
After=network-online.target

[Service]
WorkingDirectory=/opt/helios
Environment=HELIUS_API_KEY=<YOUR_HELIUS_KEY>
Environment=BIRDEYE_API_KEY=<YOUR_BIRDEYE_KEY>
ExecStart=/usr/bin/python3 -m scripts.a2_run_continuous
Restart=always
RestartSec=30
StandardOutput=append:/opt/helios/logs/a2.out
StandardError=append:/opt/helios/logs/a2.err

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /opt/helios/logs
systemctl daemon-reload
systemctl enable --now helios-a2
systemctl status helios-a2
```

Check progress: `ssh root@vps 'cat /opt/helios/logs/a2_status.json'`

---

## Recommendation

**For "I want answers in 48 hours about whether A2 has edge"**: use **Option A**. Plug in your Mac, start the script, leave it open by your desk. Free, zero setup. Come back in 2 days.

**For "I want a real autonomous bot that runs without me thinking about it"**: use **Option B (Railway)** before any live capital ever touches this. The collector is built to run 24/7; running it 24/7 is how we get the data and eventually how the live bot will execute.

**For "I'm going to scale this and want full control"**: use Option C later, once A2 (or whichever strategy survives) is proven.

---

## What I'd actually do if I were you

Start Option A today while you do other things. After 48 hours, if A2 looks viable, set up Option B before going live.

```bash
# step 1, today, takes 30 seconds:
cd /Users/isaacmineo/Main/projects/singal-flow
tmux new -s a2 './scripts/run_collector_macos.sh'
# Ctrl-b d to detach.

# step 2, anytime, takes 1 second:
cat logs/a2_status.json
```

Then go do something else for 2 days.
