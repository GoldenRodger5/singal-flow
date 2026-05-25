"""Jito Bundle submission — MEV-protected transaction delivery.

Background: when you submit a Solana transaction through the public RPC, MEV
bots see it in the mempool and can front-run/sandwich you. Jito provides a
private mempool ("block engine") where bundled transactions land atomically
without leaking. You pay a tip (in SOL) to a validator instead of priority fees.

For memecoin sniping where slippage routinely runs 10-20% with public-mempool
delivery and ~2-5% with Jito, this is one of the most valuable single upgrades
we can make to the live pipeline.

API: https://docs.jito.wtf/lowlatencytxnsend/

Usage:
    bundle = JitoBundle(rpc_url)
    sig = await bundle.send_signed_transaction(signed_tx_b64, tip_lamports=10_000)
"""
from __future__ import annotations

import os
import random
from typing import Optional

import httpx

from helios.data.adapters.base import VenueError
from helios.ops import get_logger

log = get_logger(__name__)

# Jito Block Engine regional endpoints. We pick lowest-latency per submission.
JITO_ENDPOINTS = (
    "https://mainnet.block-engine.jito.wtf/api/v1",
    "https://amsterdam.mainnet.block-engine.jito.wtf/api/v1",
    "https://frankfurt.mainnet.block-engine.jito.wtf/api/v1",
    "https://ny.mainnet.block-engine.jito.wtf/api/v1",
    "https://tokyo.mainnet.block-engine.jito.wtf/api/v1",
)

# Jito tip accounts — pay one of these as part of your transaction to be
# accepted by the block engine. List rotates; we pick uniformly at random.
JITO_TIP_ACCOUNTS = (
    "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY",
    "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDcMH",
    "ADuUkR4vqLUMWXxW9gh6D6L8pivKeVQqoZjnf21Hzs7d",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
)


def random_jito_endpoint() -> str:
    return random.choice(JITO_ENDPOINTS)


def random_tip_account() -> str:
    return random.choice(JITO_TIP_ACCOUNTS)


class JitoBundle:
    """Send a transaction through Jito's private mempool.

    Note: Jito bundles can hold up to 5 transactions submitted atomically. For
    our v1 we just submit single signed transactions ("send a bundle of one").
    Pre-bundling with a tip-transfer instruction (constructed via Jupiter swap
    builder) is the next-iteration optimization.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        tip_lamports: int = 10_000,        # default tip ≈ $0.002 at SOL=$200
    ) -> None:
        self.endpoint = endpoint or os.getenv("JITO_ENDPOINT") or random_jito_endpoint()
        self._client = client or httpx.AsyncClient(timeout=20.0)
        self.tip_lamports = tip_lamports

    async def send_signed_transaction(self, signed_tx_b64: str) -> str:
        """Submit a single pre-signed base64 tx through Jito.

        Returns the signature on success. Raises VenueError otherwise.
        """
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [signed_tx_b64, {"encoding": "base64"}],
        }
        try:
            resp = await self._client.post(f"{self.endpoint}/transactions", json=body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise VenueError(f"Jito send failed via {self.endpoint}: {e}") from e

        body = resp.json()
        if "error" in body:
            raise VenueError(f"Jito error: {body['error']}")
        sig = body.get("result")
        if not sig:
            raise VenueError(f"Jito response missing signature: {body!r}")
        log.info("jito_bundle_sent", endpoint=self.endpoint.split("//")[1].split(".")[0], signature=sig[:16] + "...")
        return sig

    async def get_bundle_status(self, bundle_id: str) -> dict:
        """Check a bundle's status (Landed/Failed/Pending)."""
        body = {
            "jsonrpc": "2.0", "id": 1,
            "method": "getInflightBundleStatuses",
            "params": [[bundle_id]],
        }
        try:
            resp = await self._client.post(f"{self.endpoint}/bundles", json=body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise VenueError(f"Jito status query failed: {e}") from e
        return resp.json().get("result", {})

    async def close(self) -> None:
        await self._client.aclose()
