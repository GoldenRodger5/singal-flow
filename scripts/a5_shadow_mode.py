"""A5 shadow runner — sentiment velocity scanner.

Run:    python -m scripts.a5_shadow_mode
Env vars (optional):
    X_API_BEARER      — X (Twitter) v2 bearer; without it X mentions are disabled
    NEYNAR_API_KEY    — Neynar Farcaster key; without it falls back to public Warpcast
"""
from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

from helios.ops import configure_logging
from helios.strategies.a5_sentiment.runner import A5ShadowRunner

load_dotenv()


async def main() -> int:
    configure_logging(level="INFO")
    runner = A5ShadowRunner()
    await runner.run()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
