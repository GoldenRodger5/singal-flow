#!/usr/bin/env bash
# A2 collector launcher for macOS — wraps the continuous runner with `caffeinate`
# so the system DOES NOT sleep while the bot is alive.
#
# Limitations of this approach (be honest with yourself):
#   * Laptop must stay open OR plugged in with clamshell mode + external display
#   * Closing the lid on battery WILL still sleep (lid-close sleep is hardwired
#     on most Mac laptops unless you use a third-party tool like Amphetamine)
#   * If you put the machine to sleep manually, the script pauses
#   * WiFi must stay on
#
# If you want true autonomy that survives lid close, suspend, reboot — deploy
# to a cloud host (see scripts/deploy_railway.md). This file is for the
# "laptop on, plugged in, I won't move it for a few days" case.
set -euo pipefail

cd "$(dirname "$0")/.."

# -d  prevent display sleep
# -i  prevent idle sleep
# -m  prevent disk sleep
# -s  prevent system sleep (only effective while on AC power)
# -u  declare user is active (extra belt-and-suspenders)
exec caffeinate -dimsu python3 -m scripts.a2_run_continuous "$@"
