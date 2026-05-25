"""Jupiter v6 swap router — quote + swap-tx construction.

API: https://station.jup.ag/docs/swap-api/swap-api
Endpoints we hit (public, rate-limited — no auth needed):
    GET  /v6/quote   → routing + expected output
    POST /v6/swap    → constructs serialized tx ready to sign

The flow is:
    quote → swap → sign (via SolanaWallet) → submit (via HeliusRPC) → confirm

For paper mode we return a synthesized Quote with simulated slippage instead
of actually building a transaction. Same code path on call sites; the wallet
+ RPC are no-ops.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import httpx

from helios.data.adapters.base import VenueError
from helios.execution.solana.rpc import HeliusRPC
from helios.execution.solana.wallet import LiveTradingDisabled, SafetyMode, SolanaWallet
from helios.ops import get_logger

log = get_logger(__name__)

JUPITER_BASE = "https://quote-api.jup.ag/v6"

# Solana wrapped SOL — the "currency" for most pairs
WSOL_MINT = "So11111111111111111111111111111111111111112"


@dataclass(frozen=True, slots=True)
class JupiterQuote:
    """A routed quote from Jupiter. Read-only."""
    input_mint: str
    output_mint: str
    in_amount: int            # base units (lamports for SOL, smallest unit for SPL)
    out_amount: int
    other_amount_threshold: int
    price_impact_pct: float
    route_plan: list[dict]
    slippage_bps: int
    raw_response: dict

    @property
    def expected_output_per_input(self) -> float:
        if self.in_amount == 0:
            return 0.0
        return self.out_amount / self.in_amount


@dataclass(frozen=True, slots=True)
class SwapResult:
    """Outcome of a swap attempt. Same shape for paper and live."""
    mode: str              # "paper" or "live"
    signature: Optional[str]
    input_mint: str
    output_mint: str
    in_amount: int
    out_amount: int
    realized_slippage_bps: float
    success: bool
    error: Optional[str] = None


class JupiterRouter:
    """Quote + swap orchestrator. Pure paper-mode by default."""

    def __init__(
        self,
        wallet: SolanaWallet,
        rpc: Optional[HeliusRPC] = None,
        client: Optional[httpx.AsyncClient] = None,
        default_slippage_bps: int = 100,           # 1% default
        priority_fee_lamports: int = 200_000,      # ~$0.04 at SOL=$200
        use_jito: bool = False,
    ) -> None:
        self.wallet = wallet
        self.rpc = rpc or HeliusRPC()
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self.default_slippage_bps = default_slippage_bps
        self.priority_fee_lamports = priority_fee_lamports
        self.use_jito = use_jito

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: Optional[int] = None,
        only_direct_routes: bool = False,
    ) -> JupiterQuote:
        """Fetch a routed quote. `amount` is in base units of the input mint."""
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": slippage_bps if slippage_bps is not None else self.default_slippage_bps,
            "onlyDirectRoutes": "true" if only_direct_routes else "false",
        }
        try:
            resp = await self._client.get(f"{JUPITER_BASE}/quote", params=params)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise VenueError(f"Jupiter quote failed for {input_mint}->{output_mint}: {e}") from e
        body = resp.json()
        if "error" in body:
            raise VenueError(f"Jupiter quote error: {body.get('error')!r}")

        return JupiterQuote(
            input_mint=body.get("inputMint", input_mint),
            output_mint=body.get("outputMint", output_mint),
            in_amount=int(body.get("inAmount", amount)),
            out_amount=int(body.get("outAmount", 0)),
            other_amount_threshold=int(body.get("otherAmountThreshold", 0)),
            price_impact_pct=float(body.get("priceImpactPct", 0.0) or 0.0),
            route_plan=body.get("routePlan", []),
            slippage_bps=int(body.get("slippageBps", params["slippageBps"])),
            raw_response=body,
        )

    async def swap(
        self,
        quote: JupiterQuote,
        max_accepted_slippage_bps: int = 500,    # 5% absolute ceiling
    ) -> SwapResult:
        """Execute the swap. In paper mode, returns a simulated SwapResult.
        In live mode, builds + signs + submits the transaction.
        """
        if quote.price_impact_pct * 100 > max_accepted_slippage_bps:
            return SwapResult(
                mode=self.wallet.mode.value,
                signature=None,
                input_mint=quote.input_mint, output_mint=quote.output_mint,
                in_amount=quote.in_amount, out_amount=0,
                realized_slippage_bps=quote.price_impact_pct * 100,
                success=False,
                error=f"price_impact {quote.price_impact_pct * 100:.0f}bps > cap {max_accepted_slippage_bps}",
            )

        # --- Paper path ---
        if self.wallet.mode != SafetyMode.LIVE or not self.wallet.can_sign:
            # Simulate with the quote's price_impact as the realized slippage
            realized = quote.price_impact_pct * 100
            log.info(
                "paper_swap",
                input=quote.input_mint[:8] + "...", output=quote.output_mint[:8] + "...",
                in_amount=quote.in_amount, out_amount=quote.out_amount,
                slippage_bps=realized,
            )
            return SwapResult(
                mode="paper", signature=None,
                input_mint=quote.input_mint, output_mint=quote.output_mint,
                in_amount=quote.in_amount, out_amount=quote.out_amount,
                realized_slippage_bps=realized, success=True,
            )

        # --- Live path ---
        return await self._live_swap(quote)

    async def _live_swap(self, quote: JupiterQuote) -> SwapResult:
        try:
            self.wallet.assert_can_sign()
        except LiveTradingDisabled as e:
            return SwapResult(
                mode="paper", signature=None,
                input_mint=quote.input_mint, output_mint=quote.output_mint,
                in_amount=quote.in_amount, out_amount=0, realized_slippage_bps=0.0,
                success=False, error=str(e),
            )

        # POST /v6/swap to build the serialized transaction
        body = {
            "quoteResponse": quote.raw_response,
            "userPublicKey": self.wallet.pubkey_str,
            "wrapAndUnwrapSol": True,
            "prioritizationFeeLamports": self.priority_fee_lamports,
            "dynamicComputeUnitLimit": True,
            "asLegacyTransaction": False,
        }
        try:
            resp = await self._client.post(f"{JUPITER_BASE}/swap", json=body)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            return SwapResult(
                mode="live", signature=None,
                input_mint=quote.input_mint, output_mint=quote.output_mint,
                in_amount=quote.in_amount, out_amount=0, realized_slippage_bps=0.0,
                success=False, error=f"Jupiter /swap failed: {e}",
            )
        swap_resp = resp.json()
        swap_tx_b64 = swap_resp.get("swapTransaction")
        if not swap_tx_b64:
            return SwapResult(
                mode="live", signature=None,
                input_mint=quote.input_mint, output_mint=quote.output_mint,
                in_amount=quote.in_amount, out_amount=0, realized_slippage_bps=0.0,
                success=False, error=f"Jupiter /swap returned no swapTransaction: {swap_resp!r}",
            )

        # Sign + submit
        try:
            signed_b64 = self.wallet.sign_transaction(swap_tx_b64)
        except LiveTradingDisabled as e:
            return SwapResult(
                mode="live", signature=None,
                input_mint=quote.input_mint, output_mint=quote.output_mint,
                in_amount=quote.in_amount, out_amount=0, realized_slippage_bps=0.0,
                success=False, error=str(e),
            )

        try:
            sig = await self.rpc.send_transaction(signed_b64, skip_preflight=True)
        except VenueError as e:
            return SwapResult(
                mode="live", signature=None,
                input_mint=quote.input_mint, output_mint=quote.output_mint,
                in_amount=quote.in_amount, out_amount=0, realized_slippage_bps=0.0,
                success=False, error=f"submit failed: {e}",
            )

        confirmed = await self.rpc.confirm_transaction(sig, max_wait_seconds=20.0)
        return SwapResult(
            mode="live", signature=sig,
            input_mint=quote.input_mint, output_mint=quote.output_mint,
            in_amount=quote.in_amount, out_amount=quote.out_amount,
            realized_slippage_bps=quote.price_impact_pct * 100,
            success=confirmed,
            error=None if confirmed else "tx not confirmed within timeout",
        )

    async def close(self) -> None:
        await self._client.aclose()
