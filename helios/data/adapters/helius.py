"""Helius adapter — Solana RPC + DAS for the authority + supply checks the
RugFilter requires.

What this fills on TokenSnapshot:
  mint_authority_renounced    via getAccountInfo (parsed) -> mintAuthority is null
  freeze_authority_renounced  via getAccountInfo (parsed) -> freezeAuthority is null
  metadata_verified           via getAsset (DAS) -> content.metadata.{name, symbol} populated

What this does NOT fill (handled by Birdeye / a future pump.fun-specific adapter):
  lp_locked_or_burned, lp_lock_pct       (requires LP token mint detection + ownership check)
  top_10_holder_pct, dev_wallet_pct      (handled by Birdeye holder endpoint)
  dev_history_known, dev_rug_history_count (requires indexed deployer history)
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from helios.data.adapters.base import VenueError
from helios.ops import get_logger

log = get_logger(__name__)

DEFAULT_RPC_BASE = "https://mainnet.helius-rpc.com"


@dataclass(frozen=True, slots=True)
class MintAuthorityInfo:
    """Full Token / Token-2022 mint state, with explicit flags for every
    extension we care about for safety.

    The dangerous Token-2022 extensions are:
      * permanentDelegate     — any wallet can transfer holders' tokens. HONEYPOT.
      * transferHook          — arbitrary code on every transfer. SELL-BLOCK RISK.
      * defaultAccountState   — if state="frozen", tokens are unsellable by default. HONEYPOT.
      * transferFeeConfig     — fee on every transfer. >1% is soft-honeypot.
      * mintCloseAuthority    — authority that can close the mint. EXFIL RISK.
      * nonTransferable       — token cannot be transferred at all. HARD HONEYPOT.

    Benign extensions (don't flag): metadataPointer, tokenMetadata, immutableOwner,
    memoTransfer, interestBearing, cpiGuard, groupPointer, tokenGroup,
    groupMemberPointer, tokenGroupMember, scaledUiAmount, confidentialTransfer.
    """
    mint_authority_renounced: bool
    freeze_authority_renounced: bool
    supply: int
    decimals: int
    # Token-2022 dangerous extensions
    has_permanent_delegate: bool = False
    has_transfer_hook: bool = False
    has_mint_close_authority: bool = False
    default_state_frozen: bool = False
    transfer_fee_basis_points: int = 0  # 0 = no fee; >100 = >1%
    is_non_transferable: bool = False
    is_token_2022: bool = False


@dataclass(frozen=True, slots=True)
class HeliusAssetInfo:
    name: str | None
    symbol: str | None
    metadata_verified: bool


class HeliusAdapter:
    def __init__(self, api_key: str | None = None, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key or os.getenv("HELIUS_API_KEY")
        if not self.api_key:
            raise ValueError("HELIUS_API_KEY env var or api_key argument required")
        self._client = client or httpx.AsyncClient(timeout=15.0)
        self._url = f"{DEFAULT_RPC_BASE}/?api-key={self.api_key}"

    async def _rpc(self, method: str, params: list) -> dict:
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        try:
            resp = await self._client.post(self._url, json=body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise VenueError(f"Helius RPC {method} failed: {e}") from e
        out = resp.json()
        if "error" in out:
            raise VenueError(f"Helius RPC {method} error: {out['error']}")
        return out.get("result", {})

    async def get_mint_authority_info(self, mint_address: str) -> MintAuthorityInfo:
        """Read the parsed SPL mint account. None on either authority = renounced."""
        result = await self._rpc(
            "getAccountInfo",
            [mint_address, {"encoding": "jsonParsed"}],
        )
        value = result.get("value")
        program = (value or {}).get("data", {}).get("program") if value else None
        if not value or program not in ("spl-token", "spl-token-2022"):
            raise VenueError(f"{mint_address} is not an SPL token mint (program={program!r})")
        info = value["data"]["parsed"]["info"]

        # Parse Token-2022 extensions (empty list for classic spl-token)
        ext_flags = {
            "has_permanent_delegate": False,
            "has_transfer_hook": False,
            "has_mint_close_authority": False,
            "default_state_frozen": False,
            "transfer_fee_basis_points": 0,
            "is_non_transferable": False,
        }
        for ext in info.get("extensions", []) or []:
            kind = ext.get("extension")
            state = ext.get("state") or {}
            if kind == "permanentDelegate":
                # If 'delegate' is non-null, an external party can move tokens.
                if state.get("delegate"):
                    ext_flags["has_permanent_delegate"] = True
            elif kind == "transferHook":
                # Active hook = programId set to non-null. Some pump.fun forks
                # use this for benign features; we treat all as risky.
                if state.get("programId"):
                    ext_flags["has_transfer_hook"] = True
            elif kind == "mintCloseAuthority":
                if state.get("closeAuthority"):
                    ext_flags["has_mint_close_authority"] = True
            elif kind == "defaultAccountState":
                # The accountState can be "initialized" (normal) or "frozen" (honeypot).
                if str(state.get("accountState", "")).lower() == "frozen":
                    ext_flags["default_state_frozen"] = True
            elif kind == "transferFeeConfig":
                # Use the *newer* fee config (newer rate is what's active on new tx).
                newer = state.get("newerTransferFee") or {}
                bps = newer.get("transferFeeBasisPoints")
                if bps is None:
                    bps = state.get("transferFeeBasisPoints", 0)
                try:
                    ext_flags["transfer_fee_basis_points"] = int(bps or 0)
                except (TypeError, ValueError):
                    ext_flags["transfer_fee_basis_points"] = 0
            elif kind == "nonTransferable":
                ext_flags["is_non_transferable"] = True

        return MintAuthorityInfo(
            mint_authority_renounced=info.get("mintAuthority") is None,
            freeze_authority_renounced=info.get("freezeAuthority") is None,
            supply=int(info.get("supply", "0")),
            decimals=int(info.get("decimals", 0)),
            is_token_2022=(program == "spl-token-2022"),
            **ext_flags,
        )

    async def get_asset_info(self, mint_address: str) -> HeliusAssetInfo:
        """DAS getAsset — name, symbol, image. Indicates metadata-verified status."""
        result = await self._rpc("getAsset", [mint_address])
        if not result:
            return HeliusAssetInfo(name=None, symbol=None, metadata_verified=False)
        md = (result.get("content") or {}).get("metadata") or {}
        name = md.get("name")
        symbol = md.get("symbol")
        return HeliusAssetInfo(
            name=name,
            symbol=symbol,
            metadata_verified=bool(name and symbol),
        )

    async def close(self) -> None:
        await self._client.aclose()
