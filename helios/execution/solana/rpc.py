"""Helius RPC client — thin HTTP + WebSocket wrapper for Solana RPC calls.

Reuses the credentials from helios.data.adapters.helius. This module is the
write-path version: it submits signed transactions and confirms them. Reads
go through the existing HeliusAdapter.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from helios.data.adapters.base import VenueError
from helios.ops import get_logger

log = get_logger(__name__)

DEFAULT_RPC_BASE = "https://mainnet.helius-rpc.com"


class HeliusRPC:
    """Solana RPC client. Same Helius key as the data adapter."""

    def __init__(self, api_key: str | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key or os.getenv("HELIUS_API_KEY")
        if not self.api_key:
            raise ValueError("HELIUS_API_KEY env var or api_key argument required")
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._url = f"{DEFAULT_RPC_BASE}/?api-key={self.api_key}"

    async def _call(self, method: str, params: list) -> Any:
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        try:
            resp = await self._client.post(self._url, json=body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise VenueError(f"Helius RPC {method} failed: {e}") from e
        out = resp.json()
        if "error" in out:
            raise VenueError(f"Helius RPC {method} error: {out['error']}")
        return out.get("result")

    async def send_transaction(
        self,
        signed_tx_b64: str,
        skip_preflight: bool = True,
        max_retries: int = 0,
        priority_fee_lamports: int | None = None,
    ) -> str:
        """Submit a signed transaction. Returns the signature.

        skip_preflight=True: skip simulation. Faster, but fails silently if the
        tx is bad. We use this in hot-path memecoin sniping where every ms matters.
        For larger / less time-sensitive trades, set False.
        """
        params: list[Any] = [
            signed_tx_b64,
            {
                "encoding": "base64",
                "skipPreflight": skip_preflight,
                "maxRetries": max_retries,
                "preflightCommitment": "processed",
            },
        ]
        sig = await self._call("sendTransaction", params)
        log.info("tx_submitted", signature=sig[:16] + "...")
        return sig

    async def confirm_transaction(self, signature: str, max_wait_seconds: float = 30.0) -> bool:
        """Poll getSignatureStatuses until confirmed or timeout. Returns True if confirmed."""
        import asyncio
        deadline = asyncio.get_event_loop().time() + max_wait_seconds
        while asyncio.get_event_loop().time() < deadline:
            statuses = await self._call(
                "getSignatureStatuses",
                [[signature], {"searchTransactionHistory": False}],
            )
            value = (statuses or {}).get("value") or []
            if value and value[0]:
                err = value[0].get("err")
                if err is None:
                    confirmation_status = value[0].get("confirmationStatus")
                    if confirmation_status in ("confirmed", "finalized"):
                        log.info("tx_confirmed", signature=signature[:16] + "...", status=confirmation_status)
                        return True
                else:
                    log.warning("tx_failed", signature=signature[:16] + "...", error=str(err))
                    return False
            await asyncio.sleep(0.4)
        log.warning("tx_confirm_timeout", signature=signature[:16] + "...")
        return False

    async def get_balance(self, pubkey: str) -> int:
        """Return SOL balance in lamports."""
        result = await self._call("getBalance", [pubkey, {"commitment": "processed"}])
        return int((result or {}).get("value", 0))

    async def get_token_balance(self, token_account: str) -> dict:
        """Return parsed SPL token balance for a token account."""
        result = await self._call("getTokenAccountBalance", [token_account, {"commitment": "processed"}])
        return (result or {}).get("value", {})

    async def close(self) -> None:
        await self._client.aclose()
