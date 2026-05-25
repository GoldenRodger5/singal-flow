"""Wallet safety tests. These are the most important tests in the project —
a regression here means real-money loss.

Every test verifies a safety invariant:
  * Paper mode is the default.
  * Live mode requires the exact safety token.
  * Observer-mode wallet can never sign.
  * The private key never appears in __repr__ / __str__.
"""
from __future__ import annotations

import pytest

from helios.execution.solana.wallet import (
    SAFETY_ENV,
    SAFETY_TOKEN,
    LiveTradingDisabled,
    SafetyMode,
    SolanaWallet,
    _current_safety_mode,
)


# ----- Mode detection -----

def test_default_mode_is_paper(monkeypatch):
    monkeypatch.delenv(SAFETY_ENV, raising=False)
    assert _current_safety_mode() == SafetyMode.PAPER


def test_live_requires_exact_token(monkeypatch):
    monkeypatch.setenv(SAFETY_ENV, "yes")  # close but wrong
    assert _current_safety_mode() == SafetyMode.PAPER

    monkeypatch.setenv(SAFETY_ENV, "I UNDERSTAND THE RISK")  # spaces, wrong
    assert _current_safety_mode() == SafetyMode.PAPER

    monkeypatch.setenv(SAFETY_ENV, SAFETY_TOKEN)
    assert _current_safety_mode() == SafetyMode.LIVE


def test_empty_env_is_paper(monkeypatch):
    monkeypatch.setenv(SAFETY_ENV, "")
    assert _current_safety_mode() == SafetyMode.PAPER


# ----- Observer construction -----

def test_observer_has_no_keypair():
    w = SolanaWallet.observer("So11111111111111111111111111111111111111112")
    assert w._keypair is None
    assert not w.can_sign


def test_observer_cannot_sign(monkeypatch):
    monkeypatch.setenv(SAFETY_ENV, SAFETY_TOKEN)  # even with live env, no key = no sign
    w = SolanaWallet.observer("So11111111111111111111111111111111111111112")
    with pytest.raises(LiveTradingDisabled, match="observer mode"):
        w.assert_can_sign()


# ----- from_env paths -----

def test_from_env_with_neither_var_raises(monkeypatch):
    monkeypatch.delenv("SOLANA_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("SOLANA_PUBKEY", raising=False)
    with pytest.raises(ValueError, match="SOLANA_PRIVATE_KEY"):
        SolanaWallet.from_env()


def test_from_env_observer_only(monkeypatch):
    monkeypatch.delenv("SOLANA_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("SOLANA_PUBKEY", "TestPubkey11111111111111111111111111111111")
    w = SolanaWallet.from_env()
    assert not w.can_sign
    assert w.pubkey_str == "TestPubkey11111111111111111111111111111111"


# ----- Secret never logged -----

def test_repr_never_includes_keypair_data(monkeypatch):
    """The __repr__ MUST NOT include the private key. We construct a fake
    keypair sentinel and check the repr contains neither the bytes nor any
    reference to it."""
    monkeypatch.setenv(SAFETY_ENV, SAFETY_TOKEN)

    class FakeKP:
        def __init__(self) -> None:
            self.secret = b"\xaa" * 32  # would be very bad to leak

    w = SolanaWallet(
        pubkey_str="TestPubkey11111111111111111111111111111111",
        _keypair=FakeKP(),
        mode=SafetyMode.LIVE,
    )
    r = repr(w)
    # Should NOT contain hex of the fake secret, the literal byte string, or the kp object
    assert "aa" * 16 not in r.lower()
    assert "\\xaa" not in r
    assert "FakeKP" not in r
    # SHOULD contain truncated pubkey (first 8 chars + "...")
    assert "TestPubk" in r
    assert "..." in r


def test_str_same_as_repr():
    w = SolanaWallet.observer("ABC123")
    assert str(w) == repr(w)


# ----- Sign requires live mode + key -----

def test_paper_mode_blocks_signing(monkeypatch):
    monkeypatch.delenv(SAFETY_ENV, raising=False)

    class FakeKP:
        def sign_message(self, _: bytes) -> bytes:
            return b"fake-signature"

    w = SolanaWallet(
        pubkey_str="TestPubkey",
        _keypair=FakeKP(),
        mode=SafetyMode.PAPER,
    )
    with pytest.raises(LiveTradingDisabled, match="Live trading disabled"):
        w.sign_message(b"hello")


def test_can_sign_property(monkeypatch):
    # Observer, paper -> False
    w1 = SolanaWallet.observer("ABC")
    assert not w1.can_sign

    # Has key, paper -> False
    class FakeKP:
        pass

    monkeypatch.delenv(SAFETY_ENV, raising=False)
    w2 = SolanaWallet(pubkey_str="X", _keypair=FakeKP(), mode=SafetyMode.PAPER)
    assert not w2.can_sign

    # Has key, live -> True
    monkeypatch.setenv(SAFETY_ENV, SAFETY_TOKEN)
    w3 = SolanaWallet(pubkey_str="X", _keypair=FakeKP(), mode=SafetyMode.LIVE)
    assert w3.can_sign
