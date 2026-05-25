"""Solana on-chain execution stack.

Three layers, three responsibilities:
    wallet.py   keypair management + signing. Never logs the secret.
    rpc.py      thin Helius RPC client (HTTP + WebSocket).
    jupiter.py  swap routing via Jupiter v6 quote+swap API.
    jito.py     bundle submission for sandwich protection.

Safety:
    SAFETY_LIVE_TRADING env var must be set to the literal string "I_UNDERSTAND_THE_RISK"
    before any code path touches a real wallet. Default = paper, hard-coded.
"""
from helios.execution.solana.wallet import (
    LiveTradingDisabled,
    SafetyMode,
    SolanaWallet,
)

__all__ = ["LiveTradingDisabled", "SafetyMode", "SolanaWallet"]
