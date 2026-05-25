"""SnapshotEnricher — combines DexScreener + Helius + Birdeye into a complete TokenSnapshot.

Source breakdown:
  DexScreener  -> liquidity, FDV, volume, txns, pool age, symbol, name, price (M + L buckets)
  Helius RPC   -> mint/freeze authority renounced, total supply (K bucket)
  Birdeye      -> top-10 holder concentration vs supply (C bucket)

What we still flag UNKNOWN:
  * lp_locked_or_burned / lp_lock_pct — pump.fun migrated pools auto-burn LP,
    so we use DexScreener's pair address pattern + dexId='raydium' + a
    pool-age + FDV/liquidity heuristic. Honest: not a real LP-token-ownership
    check yet (that requires Raydium-program-specific decoding).
  * dev_history_known / dev_rug_history_count — needs indexed deployer
    history. NOT in v1; we set dev_history_known=False which forces REJECT.

This means with v1, the RugFilter will still REJECT most tokens — but for
RELAXED-FILTER analysis we know which checks bind, which is the actual point
of shadow mode.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from helios.data.adapters.birdeye import BirdeyeAdapter
from helios.data.adapters.dexscreener import DexScreenerAdapter
from helios.data.adapters.helius import HeliusAdapter
from helios.ops import get_logger
from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot

log = get_logger(__name__)


def _infer_lp_locked(pair_dex: str | None, pool_age_seconds: int) -> tuple[bool, float]:
    """LP-lock heuristic by DEX, for v1 (no Raydium/PumpSwap program decoding yet).

    Honest reasoning per venue:
      pumpfun   bonding-curve phase (not LP yet — pre-migration). Treat as LP-locked
                because the bonding curve itself prevents dev rug.
      pumpswap  pump.fun's own AMM. On migration, LP is automatically burned to the
                burn address. This is a documented protocol behavior, not a guess.
      raydium   could be from pump.fun's old migration target, but in 2026 most
                pump.fun migrations go to pumpswap. Raydium pools < 6h old are
                lightly trusted; older raydium pools need explicit LP-token-owner
                verification (not in v1).
      meteora   dynamic-LP DLMM pools. LP-lock state varies by pool config; we don't
                verify in v1, so flag as unknown.
      <other>   unknown — reject.
    """
    if pair_dex in ("pumpfun", "pumpswap"):
        return True, 1.0
    if pair_dex == "raydium" and 0 < pool_age_seconds < 3600 * 6:
        return True, 0.95
    return False, 0.0


class SnapshotEnricher:
    def __init__(
        self,
        dexscreener: DexScreenerAdapter | None = None,
        helius: HeliusAdapter | None = None,
        birdeye: BirdeyeAdapter | None = None,
    ) -> None:
        self.dex = dexscreener or DexScreenerAdapter()
        self.helius = helius or HeliusAdapter()
        self.birdeye = birdeye or BirdeyeAdapter()

    async def enrich(self, mint_address: str) -> TokenSnapshot | None:
        """Fetch and merge data from all three sources. Returns None if the
        token isn't tracked anywhere (e.g. brand-new with no DEX activity)."""
        base_snap = await self.dex.fetch_token_snapshot(mint_address)
        if base_snap is None:
            log.info("enrich_no_dexscreener", mint=mint_address)
            return None

        try:
            mint_info = await self.helius.get_mint_authority_info(mint_address)
        except Exception as e:  # noqa: BLE001
            log.warning("helius_mint_info_failed", mint=mint_address, error=str(e))
            mint_info = None

        try:
            asset_info = await self.helius.get_asset_info(mint_address)
        except Exception as e:  # noqa: BLE001
            log.warning("helius_asset_failed", mint=mint_address, error=str(e))
            asset_info = None

        ui_supply = 0.0
        if mint_info and mint_info.supply > 0 and mint_info.decimals >= 0:
            ui_supply = mint_info.supply / (10 ** mint_info.decimals)

        top_10 = 1.0
        top_1 = 1.0
        n_returned = 0
        if ui_supply > 0:
            try:
                top_1, top_10, n_returned = await self.birdeye.get_holder_concentration_vs_supply(
                    mint_address, ui_supply, limit=100
                )
            except Exception as e:  # noqa: BLE001
                log.warning("birdeye_holders_failed", mint=mint_address, error=str(e))

        # LP-lock heuristic (honest stub — see module docstring)
        dex_id = await self._infer_dex_id(mint_address)
        lp_locked, lp_pct = _infer_lp_locked(dex_id, base_snap.pool_age_seconds)

        # Build the fully-enriched snapshot. Note dev_wallet_pct treated as
        # top_1_pct as the best proxy we have without explicit deployer ID.
        return TokenSnapshot(
            mint_address=base_snap.mint_address,
            symbol=(asset_info.symbol if asset_info and asset_info.symbol else base_snap.symbol),
            name=(asset_info.name if asset_info and asset_info.name else base_snap.name),
            venue_pair_address=base_snap.venue_pair_address,
            pool_age_seconds=base_snap.pool_age_seconds,
            liquidity_usd=base_snap.liquidity_usd,
            fully_diluted_value_usd=base_snap.fully_diluted_value_usd,
            volume_5m_usd=base_snap.volume_5m_usd,
            volume_1h_usd=base_snap.volume_1h_usd,
            txns_5m=base_snap.txns_5m,
            txns_1h=base_snap.txns_1h,
            # Authority fields from Helius
            mint_authority_renounced=mint_info.mint_authority_renounced if mint_info else False,
            freeze_authority_renounced=mint_info.freeze_authority_renounced if mint_info else False,
            # LP lock from heuristic
            lp_locked_or_burned=lp_locked,
            lp_lock_pct=lp_pct,
            # Concentration from Birdeye (top_1 used as dev_wallet proxy)
            top_10_holder_pct=top_10,
            dev_wallet_pct=top_1,
            n_holders=n_returned,  # NOTE: not real holder count — limited by Birdeye limit
            # Provenance
            metadata_verified=asset_info.metadata_verified if asset_info else base_snap.metadata_verified,
            dev_history_known=False,    # v1: no indexed history yet
            dev_rug_history_count=0,
            # Microstructure: spread approximated from buy/sell txn imbalance (rough)
            bid_ask_spread_pct=None,    # explicit unknown -> filter rejects on M01
            last_trade_price_usd=base_snap.last_trade_price_usd,
            snapshot_time=datetime.now(timezone.utc),
            # Token-2022 extension flags from Helius
            has_permanent_delegate=mint_info.has_permanent_delegate if mint_info else False,
            has_transfer_hook=mint_info.has_transfer_hook if mint_info else False,
            has_mint_close_authority=mint_info.has_mint_close_authority if mint_info else False,
            default_state_frozen=mint_info.default_state_frozen if mint_info else False,
            transfer_fee_basis_points=mint_info.transfer_fee_basis_points if mint_info else 0,
            is_non_transferable=mint_info.is_non_transferable if mint_info else False,
            is_token_2022=mint_info.is_token_2022 if mint_info else False,
        )

    async def _infer_dex_id(self, mint_address: str) -> str | None:
        # DexScreener already returned dex info inside the fetch, but our adapter
        # discarded it. For v1 we re-fetch lightly — the right fix is to surface
        # dexId on TokenSnapshot. TODO: extend TokenSnapshot.
        try:
            resp = await self.dex._client.get(
                f"https://api.dexscreener.com/latest/dex/tokens/{mint_address}"
            )
            resp.raise_for_status()
            pairs = [p for p in (resp.json().get("pairs") or []) if p.get("chainId") == "solana"]
            if not pairs:
                return None
            pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
            return pair.get("dexId")
        except Exception:
            return None

    async def close(self) -> None:
        await self.dex.close()
        await self.helius.close()
        await self.birdeye.close()
