"""Solana hot wallet — keypair management + transaction signing.

The most safety-critical module in the project. A bug here = total loss of the
wallet. Design principles:

  * **Default to paper-mode.** Live trading requires an explicit, ugly env-var
    flag the operator has to set on purpose. `SAFETY_LIVE_TRADING` must be
    literally `"I_UNDERSTAND_THE_RISK"` — typo-tolerance is anti-feature here.

  * **Never log the secret.** `__repr__` and `__str__` are overridden. The
    private key never enters loguru's formatted output.

  * **Read-only operations don't need the secret.** Address derivation and
    public balance lookup work from a public key alone — you can deploy the
    bot in observe-only mode by setting `SOLANA_PUBKEY` and omitting the
    private key entirely.

  * **One wallet, one purpose.** This wallet is exclusively for hot-path
    swap execution. Operator should rotate funds in/out manually from cold
    storage. Per-day cap enforced upstream by the risk overlay.
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from helios.ops import get_logger

log = get_logger(__name__)

SAFETY_ENV = "SAFETY_LIVE_TRADING"
SAFETY_TOKEN = "I_UNDERSTAND_THE_RISK"  # exact literal required to enable live


class LiveTradingDisabled(RuntimeError):
    """Raised when a live-only operation is attempted in paper mode."""


class SafetyMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


def _current_safety_mode() -> SafetyMode:
    """Live mode requires the exact safety token. Anything else is paper."""
    return SafetyMode.LIVE if os.getenv(SAFETY_ENV) == SAFETY_TOKEN else SafetyMode.PAPER


@dataclass
class SolanaWallet:
    """Solana hot wallet. Holds a keypair (or just a pubkey in observe-only).

    Build via:
        SolanaWallet.from_env()   reads SOLANA_PRIVATE_KEY (base58) + SOLANA_PUBKEY
        SolanaWallet.observer(pubkey)   public-key-only, can never sign
    """

    pubkey_str: str
    _keypair: Optional[object] = None  # solders.keypair.Keypair if available
    mode: SafetyMode = SafetyMode.PAPER

    def __post_init__(self) -> None:
        # Defensive: re-validate mode from env on construction so test setups
        # can flip the flag and get correct behavior.
        env_mode = _current_safety_mode()
        if self.mode != env_mode:
            self.mode = env_mode
        if self._keypair is None:
            log.info("wallet_observer_mode", pubkey=self.pubkey_str[:8] + "...")
        else:
            log.info("wallet_signer_ready", pubkey=self.pubkey_str[:8] + "...", mode=self.mode.value)

    # ----- Construction -----

    @classmethod
    def observer(cls, pubkey: str) -> SolanaWallet:
        """Public-key-only wallet. Can never sign anything."""
        return cls(pubkey_str=pubkey, _keypair=None, mode=SafetyMode.PAPER)

    @classmethod
    def from_env(cls) -> SolanaWallet:
        """Read SOLANA_PRIVATE_KEY (base58) + derive pubkey via solders.

        If SOLANA_PRIVATE_KEY is unset, falls back to observer mode using
        SOLANA_PUBKEY. If neither is set, raises ValueError.
        """
        priv_b58 = os.getenv("SOLANA_PRIVATE_KEY")
        pubkey_env = os.getenv("SOLANA_PUBKEY")

        if not priv_b58 and not pubkey_env:
            raise ValueError(
                "Neither SOLANA_PRIVATE_KEY nor SOLANA_PUBKEY set. "
                "Either provide a private key for live signing, or a public key "
                "to operate in observer-only mode."
            )

        if priv_b58:
            kp = _load_keypair_from_b58(priv_b58)
            pubkey = str(kp.pubkey()) if kp is not None else (pubkey_env or "")
            return cls(pubkey_str=pubkey, _keypair=kp, mode=_current_safety_mode())

        return cls.observer(pubkey_env)  # type: ignore[arg-type]

    # ----- Signing & live-mode guard -----

    def assert_can_sign(self) -> None:
        if self._keypair is None:
            raise LiveTradingDisabled(
                "This wallet has no private key (observer mode). "
                "Set SOLANA_PRIVATE_KEY to enable signing."
            )
        if self.mode != SafetyMode.LIVE:
            raise LiveTradingDisabled(
                f"Live trading disabled. Set env var {SAFETY_ENV}={SAFETY_TOKEN!r} "
                "to enable. (Yes, this is ugly on purpose.)"
            )

    def sign_message(self, message_bytes: bytes) -> bytes:
        """Sign a raw message. Use sparingly — most callers want sign_transaction."""
        self.assert_can_sign()
        kp = self._keypair
        # solders.keypair.Keypair.sign_message returns a Signature
        sig = kp.sign_message(message_bytes)  # type: ignore[union-attr]
        return bytes(sig)

    def sign_transaction(self, serialized_tx_b64: str) -> str:
        """Sign a base64-encoded serialized transaction (Jupiter swap returns these).

        Returns the signed transaction as base64. Caller submits to RPC.
        Raises LiveTradingDisabled in paper mode.
        """
        self.assert_can_sign()
        try:
            from solders.transaction import VersionedTransaction
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("solders not installed; cannot sign live txns") from e

        raw = base64.b64decode(serialized_tx_b64)
        tx = VersionedTransaction.from_bytes(raw)
        # Re-create with our signature(s)
        from solders.transaction import VersionedTransaction as _VT
        signed_tx = _VT(tx.message, [self._keypair])  # type: ignore[list-item]
        return base64.b64encode(bytes(signed_tx)).decode("ascii")

    # ----- Safety / observability -----

    @property
    def can_sign(self) -> bool:
        return self._keypair is not None and self.mode == SafetyMode.LIVE

    def __repr__(self) -> str:
        # Never include the private key. Pubkey shown truncated.
        suffix = "signer" if self._keypair is not None else "observer"
        truncated = (self.pubkey_str[:8] + "...") if self.pubkey_str else "?"
        return f"SolanaWallet(pubkey={truncated}, mode={self.mode.value}, role={suffix})"

    __str__ = __repr__


def _load_keypair_from_b58(b58_secret: str):  # noqa: ANN202
    """Load a solders Keypair from a base58-encoded secret-key string.

    Accepts both 64-byte (full secret-seed||pubkey) and 32-byte (seed only) formats.
    """
    try:
        from solders.keypair import Keypair
    except ImportError as e:
        raise RuntimeError(
            "solders is required for wallet operations. "
            "Add `solders` to the Helios container."
        ) from e

    import base58
    raw = base58.b58decode(b58_secret)
    if len(raw) == 64:
        return Keypair.from_bytes(raw)
    if len(raw) == 32:
        return Keypair.from_seed(raw)
    raise ValueError(f"Unexpected secret length {len(raw)}; expected 32 or 64 bytes")
