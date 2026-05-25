"""RugFilter — pure logic that decides if a TokenSnapshot is tradeable.

THIS IS THE EDGE of A2. Every check here is something a competent on-chain
analyst would verify before clicking buy on a freshly-launched token. The bot's
job is to run all of them in milliseconds and refuse to trade unless every
check passes.

Design constraints:
  * Pure function. No I/O. Same input → same decision.
  * Every rejection carries a machine-readable code so we can audit which checks
    are most binding in shadow mode and re-calibrate.
  * "Unknown" data is treated as failing the check, NEVER as passing. Adapters
    are responsible for filling in TokenSnapshot fields; if they can't, the
    filter rejects.

The checks fall into five buckets:
  K  Authorities      — can the dev mint, freeze, or pull LP?
  C  Concentration    — how much is owned by the top wallets / dev?
  L  Liquidity        — is there enough float and depth to actually trade?
  P  Provenance       — is the metadata real, and what's the deployer's history?
  M  Microstructure   — is the spread tradeable now?
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot


class FilterDecision(str, Enum):
    PASS = "PASS"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class FilterConfig:
    """Reasonable defaults for memecoin sniping on Solana in 2026."""

    # Liquidity
    min_liquidity_usd: Decimal = Decimal("15000")     # below this, depth is too thin
    max_liquidity_usd: Decimal = Decimal("5000000")   # above this, it's not a fresh launch
    min_pool_age_seconds: int = 30                    # too young = first-block bots only
    max_pool_age_seconds: int = 1800                  # > 30 min = no longer fresh
    min_volume_5m_usd: Decimal = Decimal("3000")
    min_txns_5m: int = 25                             # low txns = wash-trade-only suspicion

    # Authorities (HARD requirements)
    require_mint_renounced: bool = True
    require_freeze_renounced: bool = True
    require_lp_locked: bool = True
    min_lp_lock_pct: float = 0.90                     # 90%+ of LP locked/burned

    # Token-2022 dangerous extensions — ALL of these are hard rejects.
    # transfer_fee threshold: anything > 100 bps (1%) is a soft honeypot.
    max_transfer_fee_basis_points: int = 100

    # Concentration
    max_top_10_holder_pct: float = 0.30               # >30% in top 10 = too concentrated
    max_dev_wallet_pct: float = 0.05                  # >5% still in dev wallet = exit-liq risk
    min_n_holders: int = 75

    # Provenance
    require_metadata_verified: bool = True
    max_dev_rug_history_count: int = 0                # any prior rug = reject

    # Microstructure
    max_bid_ask_spread_pct: float = 0.05              # >5% spread = bot trap

    # FDV sanity: avoid tokens already pumped to silly multiples
    max_fdv_to_liquidity_ratio: float = 20.0


# Keep a friendlier alias to match docstring naming
RugFilterConfig = FilterConfig


@dataclass(frozen=True, slots=True)
class FilterReport:
    decision: FilterDecision
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.decision == FilterDecision.PASS


class RugFilter:
    """Apply the full check battery. Short-circuits at first hard-reject (K-bucket)
    but collects ALL failing checks otherwise — useful for shadow-mode audit
    (we want to know if 80% of fails are concentration vs 20% are LP-not-locked,
    because that informs threshold tuning)."""

    def __init__(self, config: FilterConfig | None = None) -> None:
        self.config = config or FilterConfig()

    def check(self, snap: TokenSnapshot) -> FilterReport:
        cfg = self.config
        reasons: list[str] = []

        # ---- K: Authorities (hard rejects, evaluated first) ----
        if cfg.require_mint_renounced and not snap.mint_authority_renounced:
            return FilterReport(FilterDecision.REJECT, ("K01_mint_authority_active",))
        if cfg.require_freeze_renounced and not snap.freeze_authority_renounced:
            return FilterReport(FilterDecision.REJECT, ("K02_freeze_authority_active",))
        if cfg.require_lp_locked and not snap.lp_locked_or_burned:
            return FilterReport(FilterDecision.REJECT, ("K03_lp_not_locked",))
        if snap.lp_lock_pct < cfg.min_lp_lock_pct:
            return FilterReport(FilterDecision.REJECT, (f"K04_lp_lock_pct_{snap.lp_lock_pct:.2f}_below_{cfg.min_lp_lock_pct:.2f}",))

        # Token-2022 dangerous-extension short-circuits
        if snap.has_permanent_delegate:
            return FilterReport(FilterDecision.REJECT, ("K05_permanent_delegate_set_honeypot",))
        if snap.has_transfer_hook:
            return FilterReport(FilterDecision.REJECT, ("K06_transfer_hook_set_sell_block_risk",))
        if snap.has_mint_close_authority:
            return FilterReport(FilterDecision.REJECT, ("K07_mint_close_authority_set",))
        if snap.default_state_frozen:
            return FilterReport(FilterDecision.REJECT, ("K08_default_state_frozen_honeypot",))
        if snap.is_non_transferable:
            return FilterReport(FilterDecision.REJECT, ("K10_non_transferable_hard_honeypot",))
        if snap.transfer_fee_basis_points > cfg.max_transfer_fee_basis_points:
            return FilterReport(FilterDecision.REJECT, (f"K09_transfer_fee_{snap.transfer_fee_basis_points}_bps_above_{cfg.max_transfer_fee_basis_points}_bps",))

        # ---- L: Liquidity ----
        if snap.liquidity_usd < cfg.min_liquidity_usd:
            reasons.append(f"L01_liquidity_${snap.liquidity_usd}_below_${cfg.min_liquidity_usd}")
        if snap.liquidity_usd > cfg.max_liquidity_usd:
            reasons.append(f"L02_liquidity_${snap.liquidity_usd}_above_${cfg.max_liquidity_usd}_not_fresh")
        if snap.pool_age_seconds < cfg.min_pool_age_seconds:
            reasons.append(f"L03_pool_age_{snap.pool_age_seconds}s_below_{cfg.min_pool_age_seconds}s")
        if snap.pool_age_seconds > cfg.max_pool_age_seconds:
            reasons.append(f"L04_pool_age_{snap.pool_age_seconds}s_above_{cfg.max_pool_age_seconds}s")
        if snap.volume_5m_usd < cfg.min_volume_5m_usd:
            reasons.append(f"L05_volume_5m_${snap.volume_5m_usd}_below_${cfg.min_volume_5m_usd}")
        if snap.txns_5m < cfg.min_txns_5m:
            reasons.append(f"L06_txns_5m_{snap.txns_5m}_below_{cfg.min_txns_5m}")
        if snap.liquidity_usd > 0:
            fdv_ratio = float(snap.fully_diluted_value_usd / snap.liquidity_usd)
            if fdv_ratio > cfg.max_fdv_to_liquidity_ratio:
                reasons.append(f"L07_fdv_liq_ratio_{fdv_ratio:.1f}_above_{cfg.max_fdv_to_liquidity_ratio}")

        # ---- C: Concentration ----
        if snap.top_10_holder_pct > cfg.max_top_10_holder_pct:
            reasons.append(f"C01_top10_{snap.top_10_holder_pct:.2%}_above_{cfg.max_top_10_holder_pct:.2%}")
        if snap.dev_wallet_pct > cfg.max_dev_wallet_pct:
            reasons.append(f"C02_dev_wallet_{snap.dev_wallet_pct:.2%}_above_{cfg.max_dev_wallet_pct:.2%}")
        if snap.n_holders < cfg.min_n_holders:
            reasons.append(f"C03_holders_{snap.n_holders}_below_{cfg.min_n_holders}")

        # ---- P: Provenance ----
        if cfg.require_metadata_verified and not snap.metadata_verified:
            reasons.append("P01_metadata_not_verified")
        if not snap.dev_history_known:
            # Unknown history = REJECT, not pass. Adapter must populate this.
            reasons.append("P02_dev_history_unknown")
        elif snap.dev_rug_history_count > cfg.max_dev_rug_history_count:
            reasons.append(f"P03_dev_prior_rugs_{snap.dev_rug_history_count}_above_{cfg.max_dev_rug_history_count}")

        # ---- M: Microstructure ----
        if snap.bid_ask_spread_pct is None:
            reasons.append("M01_spread_unknown")
        elif snap.bid_ask_spread_pct > cfg.max_bid_ask_spread_pct:
            reasons.append(f"M02_spread_{snap.bid_ask_spread_pct:.2%}_above_{cfg.max_bid_ask_spread_pct:.2%}")

        if reasons:
            return FilterReport(FilterDecision.REJECT, tuple(reasons))
        return FilterReport(FilterDecision.PASS, ())
