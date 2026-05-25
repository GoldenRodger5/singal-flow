"""Tests for the A2 RugFilter.

The filter is safety-critical: a single false-pass on a rug = total loss of
that position. Tests below cover every rejection code + the property that a
fully-default snapshot (all "unknown" fields) NEVER passes.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from helios.strategies.a2_meme_snipe.rug_filter import (
    FilterConfig,
    FilterDecision,
    RugFilter,
)
from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot


def _good() -> TokenSnapshot:
    """A snapshot of a token that should PASS the default filter."""
    return TokenSnapshot(
        mint_address="GoodMint11111111111111111111111111111111111",
        symbol="GOOD", name="Good Token",
        venue_pair_address="Pair1",
        pool_age_seconds=300,                            # 5 min
        liquidity_usd=Decimal("100000"),
        fully_diluted_value_usd=Decimal("500000"),       # 5x liquidity, fine
        volume_5m_usd=Decimal("25000"),
        volume_1h_usd=Decimal("150000"),
        txns_5m=120,
        txns_1h=900,
        mint_authority_renounced=True,
        freeze_authority_renounced=True,
        lp_locked_or_burned=True,
        lp_lock_pct=0.98,
        top_10_holder_pct=0.18,
        dev_wallet_pct=0.01,
        n_holders=400,
        metadata_verified=True,
        dev_history_known=True,
        dev_rug_history_count=0,
        bid_ask_spread_pct=0.012,
        last_trade_price_usd=Decimal("0.0042"),
        snapshot_time=datetime.now(timezone.utc),
    )


@pytest.fixture
def f() -> RugFilter:
    return RugFilter()


def test_good_token_passes(f):
    report = f.check(_good())
    assert report.decision == FilterDecision.PASS, f"expected PASS, got {report.reasons}"


def test_K01_mint_authority_active_rejects(f):
    s = replace(_good(), mint_authority_renounced=False)
    r = f.check(s)
    assert not r.passed
    assert any("K01" in code for code in r.reasons)


def test_K02_freeze_authority_active_rejects(f):
    s = replace(_good(), freeze_authority_renounced=False)
    r = f.check(s)
    assert not r.passed
    assert any("K02" in code for code in r.reasons)


def test_K03_lp_not_locked_rejects(f):
    s = replace(_good(), lp_locked_or_burned=False)
    r = f.check(s)
    assert not r.passed
    assert any("K03" in code for code in r.reasons)


def test_K04_lp_lock_pct_too_low(f):
    s = replace(_good(), lp_lock_pct=0.5)
    r = f.check(s)
    assert not r.passed
    assert any("K04" in code for code in r.reasons)


def test_L01_low_liquidity(f):
    s = replace(_good(), liquidity_usd=Decimal("5000"))
    r = f.check(s)
    assert not r.passed
    assert any("L01" in code for code in r.reasons)


def test_L02_high_liquidity_not_fresh(f):
    s = replace(_good(), liquidity_usd=Decimal("20000000"))
    r = f.check(s)
    assert not r.passed
    assert any("L02" in code for code in r.reasons)


def test_L03_too_young(f):
    s = replace(_good(), pool_age_seconds=5)
    r = f.check(s)
    assert not r.passed
    assert any("L03" in code for code in r.reasons)


def test_L04_too_old(f):
    s = replace(_good(), pool_age_seconds=10000)
    r = f.check(s)
    assert not r.passed
    assert any("L04" in code for code in r.reasons)


def test_C01_top10_concentration(f):
    s = replace(_good(), top_10_holder_pct=0.6)
    r = f.check(s)
    assert not r.passed
    assert any("C01" in code for code in r.reasons)


def test_C02_dev_wallet_too_big(f):
    s = replace(_good(), dev_wallet_pct=0.15)
    r = f.check(s)
    assert not r.passed
    assert any("C02" in code for code in r.reasons)


def test_P02_unknown_dev_rejects(f):
    """The deployer being totally unknown is a REJECTION, never a pass."""
    s = replace(_good(), dev_history_known=False)
    r = f.check(s)
    assert not r.passed
    assert any("P02" in code for code in r.reasons)


def test_P03_prior_rug_history(f):
    s = replace(_good(), dev_rug_history_count=2)
    r = f.check(s)
    assert not r.passed
    assert any("P03" in code for code in r.reasons)


def test_M01_unknown_spread(f):
    s = replace(_good(), bid_ask_spread_pct=None)
    r = f.check(s)
    assert not r.passed
    assert any("M01" in code for code in r.reasons)


def test_M02_spread_too_wide(f):
    s = replace(_good(), bid_ask_spread_pct=0.20)
    r = f.check(s)
    assert not r.passed
    assert any("M02" in code for code in r.reasons)


def test_L07_fdv_to_liquidity_ratio(f):
    s = replace(_good(), fully_diluted_value_usd=Decimal("5000000"))  # 50x liquidity
    r = f.check(s)
    assert not r.passed
    assert any("L07" in code for code in r.reasons)


def test_default_unknown_snapshot_rejects(f):
    """SAFETY: a snapshot with all unknowns / hostile defaults must REJECT.
    This is the property that protects us from adapters that fail to fill
    authority fields — silence must never be confused with safety.
    """
    s = TokenSnapshot(
        mint_address="x", symbol="x", name="x", venue_pair_address="x",
        pool_age_seconds=0,
        liquidity_usd=Decimal("0"),
        fully_diluted_value_usd=Decimal("0"),
        volume_5m_usd=Decimal("0"), volume_1h_usd=Decimal("0"),
        txns_5m=0, txns_1h=0,
        # All authority/concentration/provenance hostile defaults:
        mint_authority_renounced=False, freeze_authority_renounced=False,
        lp_locked_or_burned=False, lp_lock_pct=0.0,
        top_10_holder_pct=1.0, dev_wallet_pct=1.0, n_holders=0,
        metadata_verified=False, dev_history_known=False, dev_rug_history_count=0,
        bid_ask_spread_pct=None, last_trade_price_usd=Decimal("0"),
        snapshot_time=datetime.now(timezone.utc),
    )
    r = f.check(s)
    assert r.decision == FilterDecision.REJECT


def test_hard_K_reject_short_circuits(f):
    """K-bucket rejections short-circuit; we should see exactly one K reason
    and no L/C/M reasons (even though the snapshot has other problems too)."""
    s = replace(_good(),
                mint_authority_renounced=False,
                liquidity_usd=Decimal("100"),
                top_10_holder_pct=0.99)
    r = f.check(s)
    assert len(r.reasons) == 1
    assert r.reasons[0].startswith("K01")


def test_K05_permanent_delegate_rejects(f):
    s = replace(_good(), has_permanent_delegate=True)
    r = f.check(s)
    assert not r.passed
    assert any("K05" in code for code in r.reasons)


def test_K06_transfer_hook_rejects(f):
    s = replace(_good(), has_transfer_hook=True)
    r = f.check(s)
    assert not r.passed
    assert any("K06" in code for code in r.reasons)


def test_K07_mint_close_authority_rejects(f):
    s = replace(_good(), has_mint_close_authority=True)
    r = f.check(s)
    assert not r.passed
    assert any("K07" in code for code in r.reasons)


def test_K08_default_state_frozen_rejects(f):
    s = replace(_good(), default_state_frozen=True)
    r = f.check(s)
    assert not r.passed
    assert any("K08" in code for code in r.reasons)


def test_K09_high_transfer_fee_rejects(f):
    s = replace(_good(), transfer_fee_basis_points=500)  # 5% fee
    r = f.check(s)
    assert not r.passed
    assert any("K09" in code for code in r.reasons)


def test_K09_low_transfer_fee_passes(f):
    s = replace(_good(), transfer_fee_basis_points=30)  # 0.3% — fine
    r = f.check(s)
    assert r.passed


def test_K10_non_transferable_rejects(f):
    s = replace(_good(), is_non_transferable=True)
    r = f.check(s)
    assert not r.passed
    assert any("K10" in code for code in r.reasons)


def test_token_2022_with_only_benign_extensions_passes(f):
    """Pump.fun token shape: spl-token-2022 with metadataPointer + tokenMetadata
    (both benign) and all dangerous-extension flags False. Should PASS."""
    s = replace(_good(), is_token_2022=True)
    r = f.check(s)
    assert r.passed, f"got reasons: {r.reasons}"


def test_tighter_config_rejects_borderline(f):
    """Calibration sanity: a stricter config rejects what default passes."""
    s = _good()
    assert f.check(s).passed
    strict = RugFilter(FilterConfig(min_liquidity_usd=Decimal("1000000")))
    assert not strict.check(s).passed
