"""A3 shadow runner — liquidation cascade detection on BTC/ETH/SOL perps.

Logs to /data/logs/a3_shadow.jsonl. Same pattern as A2 shadow: collect signals
+ outcomes, calibrate later.

Run:    python -m scripts.a3_shadow_mode
"""
from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

from helios.ops import configure_logging
from helios.strategies.a3_liq_hunt.runner import A3ShadowRunner

load_dotenv()


async def main() -> int:
    configure_logging(level="INFO")
    runner = A3ShadowRunner()
    await runner.run()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
