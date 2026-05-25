"""DexScreener adapter — public, no-auth snapshot data for Solana tokens.

What it gives us (FREE):
  * Current liquidity, FDV, 5m/1h volume + txn count, price
  * Top pairs for a token, basic metadata

What it DOES NOT give us:
  * On-chain authorities (mint/freeze renounced, LP locked)  — need Solana RPC (Helius)
  * Top holders concentration                                 — need Solana RPC / Solscan
  * Dev wallet history                                        — need indexed dataset (Helius / Bitquery)

So DexScreener alone is INSUFFICIENT for the RugFilter to pass any token.
The fields it can't fill come from later adapters (Phase 2.2) — for now
DexScreener fills the M (microstructure) and L (liquidity) buckets, and the
RugFilter correctly REJECTS any token whose K/C/P fields default to unknown.

This is intentional: the system is safe by default. Until we wire authority
checks, no token can pass — which is the right behavior before live capital.

API: https://docs.dexscreener.com/api/reference
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import httpx

from helios.data.adapters.base import VenueError
from helios.ops import get_logger
from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot

log = get_logger(__name__)

DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex"


def _dec(x, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(x)) if x is not None else default
    except Exception:
        return default


def _int(x, default: int = 0) -> int:
    try:
        return int(x) if x is not None else default
    except Exception:
        return default


class DexScreenerAdapter:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=15.0)

    async def fetch_token_snapshot(self, mint_address: str) -> TokenSnapshot | None:
        """Return a TokenSnapshot for the most-liquid Solana pair of this mint,
        or None if the mint isn't tracked. Authority and concentration fields
        default to UNKNOWN (False / 0), which causes the RugFilter to reject —
        a separate adapter must fill them before any trade can pass."""
        url = f"{DEXSCREENER_BASE}/tokens/{mint_address}"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise VenueError(f"DexScreener fetch failed for {mint_address}: {e}") from e

        body = resp.json()
        pairs = body.get("pairs") or []
        solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
        if not solana_pairs:
            return None
        # Pick the most-liquid pair
        pair = max(solana_pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))

        base = pair.get("baseToken") or {}
        liquidity = (pair.get("liquidity") or {}).get("usd") or 0
        fdv = pair.get("fdv") or 0
        vol5m = (pair.get("volume") or {}).get("m5") or 0
        vol1h = (pair.get("volume") or {}).get("h1") or 0
        txns_5m = ((pair.get("txns") or {}).get("m5") or {})
        txns_1h = ((pair.get("txns") or {}).get("h1") or {})
        buys_5m = _int(txns_5m.get("buys"))
        sells_5m = _int(txns_5m.get("sells"))
        n_5m = buys_5m + sells_5m
        n_1h = _int(txns_1h.get("buys")) + _int(txns_1h.get("sells"))

        # Approximate spread from buy/sell imbalance + activity. Heuristic:
        # well-balanced (ratio 0.4-0.6) AND high activity (>50 txns/5m) => ~3% spread.
        # Heavily skewed or low activity => unknown (filter rejects).
        spread_pct: float | None = None
        if n_5m >= 50 and buys_5m > 0 and sells_5m > 0:
            ratio = buys_5m / n_5m
            if 0.30 <= ratio <= 0.70:
                # Map balance to spread: perfectly balanced -> 2%, edge of band -> 4%
                imbalance = abs(ratio - 0.5) / 0.20  # 0..1 within band
                spread_pct = 0.02 + imbalance * 0.02

        pair_created_ms = pair.get("pairCreatedAt")
        if pair_created_ms:
            created = datetime.fromtimestamp(int(pair_created_ms) / 1000, tz=timezone.utc)
            age_seconds = int((datetime.now(timezone.utc) - created).total_seconds())
        else:
            age_seconds = 0

        last_price = pair.get("priceUsd") or 0

        return TokenSnapshot(
            mint_address=base.get("address") or mint_address,
            symbol=base.get("symbol") or "?",
            name=base.get("name") or "?",
            venue_pair_address=pair.get("pairAddress") or "",
            pool_age_seconds=age_seconds,
            liquidity_usd=_dec(liquidity),
            fully_diluted_value_usd=_dec(fdv),
            volume_5m_usd=_dec(vol5m),
            volume_1h_usd=_dec(vol1h),
            txns_5m=n_5m,
            txns_1h=n_1h,
            # Fields DexScreener doesn't surface — default to UNKNOWN/false so
            # the RugFilter rejects until authority adapter (Phase 2.2) lands.
            mint_authority_renounced=False,
            freeze_authority_renounced=False,
            lp_locked_or_burned=False,
            lp_lock_pct=0.0,
            top_10_holder_pct=1.0,
            dev_wallet_pct=1.0,
            n_holders=0,
            metadata_verified=bool(base.get("symbol") and base.get("name")),
            dev_history_known=False,
            dev_rug_history_count=0,
            bid_ask_spread_pct=spread_pct,
            last_trade_price_usd=_dec(last_price),
            snapshot_time=datetime.now(timezone.utc),
        )

    async def close(self) -> None:
        await self._client.aclose()
