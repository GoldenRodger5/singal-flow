"""TokenSnapshot — point-in-time view of a Solana token + its DEX pool.

Sourced by an adapter (DexScreener for snapshots, Helius RPC for live detection,
Birdeye for historical replay). The RugFilter operates exclusively over this
structure — adapters do the IO, the filter is pure logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class HolderInfo:
    address: str
    pct_supply: float  # fraction of circulating supply, [0, 1]


@dataclass(frozen=True, slots=True)
class TokenSnapshot:
    """All the signal we need to decide if a token is tradeable.

    Required fields are non-Optional. Optional fields can be missing if the
    adapter doesn't surface them — the filter handles missing data with explicit
    rejection codes (UNKNOWN_X), never silently passes.
    """
    # Identity
    mint_address: str
    symbol: str
    name: str
    venue_pair_address: str  # the DEX pool address

    # Pool / liquidity
    pool_age_seconds: int                # how old is the pool we'd trade against
    liquidity_usd: Decimal               # current LP value in USD
    fully_diluted_value_usd: Decimal
    volume_5m_usd: Decimal
    volume_1h_usd: Decimal
    txns_5m: int
    txns_1h: int

    # Token authorities (Solana SPL)
    mint_authority_renounced: bool       # if False, dev can mint more supply
    freeze_authority_renounced: bool     # if False, dev can freeze your wallet
    lp_locked_or_burned: bool            # LP tokens out of dev control
    lp_lock_pct: float                   # fraction of LP locked/burned, [0, 1]

    # Concentration
    top_10_holder_pct: float             # fraction of supply in top 10 wallets
    dev_wallet_pct: float                # fraction of supply still in deployer wallet
    n_holders: int

    # Provenance
    metadata_verified: bool              # token has on-chain metadata (name, symbol, image)
    dev_history_known: bool              # we have history for this deployer wallet
    dev_rug_history_count: int           # number of prior rug-pattern launches by deployer (0 if unknown but tagged via dev_history_known)

    # Current market microstructure
    bid_ask_spread_pct: float | None     # mid-price spread, fraction
    last_trade_price_usd: Decimal

    snapshot_time: datetime

    # Token-2022 dangerous-extension flags. Default safe-side (False / 0) for
    # backward compat; the RugFilter rejects on any True / high-fee value.
    has_permanent_delegate: bool = False         # K05 — HONEYPOT
    has_transfer_hook: bool = False              # K06 — sell-block risk
    has_mint_close_authority: bool = False       # K07 — exfil risk
    default_state_frozen: bool = False           # K08 — HONEYPOT
    transfer_fee_basis_points: int = 0           # K09 — >100 bps suspect
    is_non_transferable: bool = False            # K10 — HARD HONEYPOT
    is_token_2022: bool = False                  # informational only
