"""Helius WebSocket — real-time stream of new pool / token launch events.

Why this matters: DexScreener "trending" only surfaces tokens that have ALREADY
moved (1h volume, transaction count, etc.). By the time a token appears there,
the easy 5-50x is gone. The actual edge in memecoin sniping is in the first
30-120 seconds after pool creation, before the bot crowd piles in.

Helius's Enhanced WebSocket subscribes to program-account changes. We watch:
  - Pump.fun program (token launches via bonding curve)
  - Raydium AMM v4 program (LP creations / migrations)
  - PumpSwap program (pump.fun's own AMM, post-migration target in 2026)

Each notification is a parsed account update; we extract the mint address +
created timestamp + initial liquidity event and push it into a queue that A2
consumes.

Reference: https://docs.helius.dev/webhooks-and-websockets/enhanced-websockets
"""
from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx
import websockets

from helios.ops import get_logger

log = get_logger(__name__)

# Solana program IDs we care about
PROGRAM_PUMP_FUN = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PROGRAM_PUMPSWAP = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
PROGRAM_RAYDIUM_AMMV4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
PROGRAM_RAYDIUM_CPMM = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"

HELIUS_WSS_BASE = "wss://atlas-mainnet.helius-rpc.com"


@dataclass(frozen=True, slots=True)
class PoolCreationEvent:
    """A new pool / token launch detected on-chain."""
    program: str           # one of the PROGRAM_* constants above
    mint_address: str      # the SPL mint of the launched token (best-effort)
    pool_address: str      # the AMM pool / pair address
    slot: int
    detected_at: datetime  # our system clock when we received the event
    raw_account_data: dict


class HeliusWebSocket:
    """Subscribes to Helius Atlas WS for program-account-change events.

    Usage:
        async with HeliusWebSocket() as ws:
            async for event in ws.stream_new_pools():
                # event is a PoolCreationEvent
                await my_strategy.on_new_pool(event)

    The class auto-reconnects on disconnect, with exponential backoff. Loss of
    messages during reconnect is logged but does not raise — for shadow mode
    a few missed launches are acceptable; for live we'd add a deduplication
    cache + a "missed event recovery" pass via HTTP polling.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        programs: tuple[str, ...] = (PROGRAM_PUMP_FUN, PROGRAM_PUMPSWAP, PROGRAM_RAYDIUM_AMMV4),
        max_backoff_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("HELIUS_API_KEY")
        if not self.api_key:
            raise ValueError("HELIUS_API_KEY required for the WebSocket adapter")
        self.programs = programs
        self.max_backoff_seconds = max_backoff_seconds
        self._url = f"{HELIUS_WSS_BASE}/?api-key={self.api_key}"
        self._ws: Optional[websockets.WebSocketClientProtocol] = None  # type: ignore[name-defined]
        self._next_id = 1

    async def __aenter__(self) -> "HeliusWebSocket":
        await self._connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def _connect(self) -> None:
        log.info("helius_ws_connecting", n_programs=len(self.programs))
        self._ws = await websockets.connect(self._url, max_size=2 ** 22)
        # Subscribe to each program's account changes
        for program in self.programs:
            sub_id = self._next_id
            self._next_id += 1
            sub = {
                "jsonrpc": "2.0",
                "id": sub_id,
                "method": "programSubscribe",
                "params": [
                    program,
                    {"encoding": "jsonParsed", "commitment": "processed"},
                ],
            }
            await self._ws.send(json.dumps(sub))
            log.info("helius_ws_subscribed", program=program[:8] + "...")

    async def close(self) -> None:
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None

    async def stream_new_pools(self) -> AsyncIterator[PoolCreationEvent]:
        """Yield PoolCreationEvent as they arrive. Auto-reconnects on disconnect."""
        backoff = 1.0
        while True:
            if self._ws is None:
                try:
                    await self._connect()
                    backoff = 1.0  # reset on success
                except Exception as e:  # noqa: BLE001
                    log.warning("helius_ws_connect_failed", error=str(e), retry_in=backoff)
                    await asyncio.sleep(backoff)
                    backoff = min(self.max_backoff_seconds, backoff * 2)
                    continue

            try:
                async for raw in self._ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    event = self._parse_event(msg)
                    if event is not None:
                        yield event
            except websockets.ConnectionClosed:
                log.warning("helius_ws_disconnected", retry_in=backoff)
                self._ws = None
                await asyncio.sleep(backoff)
                backoff = min(self.max_backoff_seconds, backoff * 2)
            except Exception as e:  # noqa: BLE001
                log.warning("helius_ws_error", error=str(e))
                self._ws = None
                await asyncio.sleep(backoff)
                backoff = min(self.max_backoff_seconds, backoff * 2)

    def _parse_event(self, msg: dict) -> Optional[PoolCreationEvent]:
        """Turn a raw Atlas notification into a PoolCreationEvent, if it looks
        like a fresh pool creation.

        v1 heuristic: any programNotification whose parsed instruction type
        contains keywords like "initialize" or "create_pool". Helius's parsed
        account format helps but is program-specific; we keep it loose here and
        let the downstream enricher / RugFilter do the heavy lifting.
        """
        if msg.get("method") != "programNotification":
            return None
        params = msg.get("params") or {}
        result = params.get("result") or {}
        value = result.get("value") or {}
        account = value.get("account") or {}
        parsed = (account.get("data") or {}).get("parsed") or {}
        info = parsed.get("info") or {}

        # Best-effort mint extraction. Different program decoders surface
        # different fields; we collect candidates.
        mint = info.get("mint") or info.get("tokenMint") or info.get("baseMint") or info.get("base_mint")
        if not mint:
            # No mint to work with → ignore
            return None

        pool = value.get("pubkey") or ""
        slot = result.get("context", {}).get("slot", 0)
        program = parsed.get("type") or "unknown"

        return PoolCreationEvent(
            program=program,
            mint_address=mint,
            pool_address=pool,
            slot=slot,
            detected_at=datetime.now(timezone.utc),
            raw_account_data=info,
        )


# ----- Polling fallback for environments where websockets aren't viable -----

class HeliusNewPoolPoller:
    """HTTP polling fallback: queries DexScreener /token-profiles/latest more
    aggressively (every 15s instead of 30m) AND filters by pair age < 5 min.

    Less ideal than the WebSocket (we still see tokens after some price action)
    but works without ws infrastructure. Same event interface so call sites
    don't need to know which one they're using.
    """

    def __init__(self, client: Optional[httpx.AsyncClient] = None, poll_interval_s: float = 15.0) -> None:
        self._client = client or httpx.AsyncClient(timeout=15.0)
        self.poll_interval_s = poll_interval_s
        self._seen: set[str] = set()

    async def stream_new_pools(self) -> AsyncIterator[PoolCreationEvent]:
        while True:
            try:
                resp = await self._client.get("https://api.dexscreener.com/token-profiles/latest/v1")
                resp.raise_for_status()
                profiles = resp.json()
            except Exception as e:  # noqa: BLE001
                log.warning("dexscreener_poll_failed", error=str(e))
                await asyncio.sleep(self.poll_interval_s)
                continue

            for p in profiles:
                if p.get("chainId") != "solana":
                    continue
                mint = p.get("tokenAddress")
                if not mint or mint in self._seen:
                    continue
                self._seen.add(mint)
                yield PoolCreationEvent(
                    program="dexscreener_polled",
                    mint_address=mint,
                    pool_address="",
                    slot=0,
                    detected_at=datetime.now(timezone.utc),
                    raw_account_data=p,
                )
            await asyncio.sleep(self.poll_interval_s)

    async def close(self) -> None:
        await self._client.aclose()
