"""A2 LIVE runner — connects the dots between Helius websocket events and the
Jupiter swap executor.

Pipeline:
    PoolCreationEvent  (from helios.data.adapters.helius_ws)
        ↓
    SnapshotEnricher   (DexScreener + Helius RPC + Birdeye)
        ↓
    RugFilter          (the K/L/C/P/M battery)
        ↓
    pre-trade Jupiter quote
        ↓
    SwapResult         (paper or live)
        ↓
    PositionManager    (trailing stop, hard exit, time-based exit)
        ↓
    write outcome to /data/logs/a2_live_fills.jsonl

This is the live-mode counterpart to scripts/a2_run_continuous.py (which is
shadow-only). Both run in parallel for now: shadow keeps logging, live runs
paper swaps. Once shadow data confirms edge, the same code path goes live by
flipping SAFETY_LIVE_TRADING.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from helios.data.adapters.helius_ws import (
    HeliusNewPoolPoller,
    HeliusWebSocket,
    PoolCreationEvent,
)
from helios.execution.solana.jito import JitoBundle
from helios.execution.solana.jupiter import WSOL_MINT, JupiterRouter, SwapResult
from helios.execution.solana.rpc import HeliusRPC
from helios.execution.solana.wallet import SafetyMode, SolanaWallet
from helios.ops import get_logger
from helios.strategies.a2_meme_snipe import RugFilter
from helios.strategies.a2_meme_snipe.enricher import SnapshotEnricher
from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot

log = get_logger(__name__)

LIVE_FILLS_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "a2_live_fills.jsonl"


@dataclass
class LivePosition:
    """An open A2 position. Tracked entirely in memory for v1; restart = forget.
    (Acceptable for shadow; live should add persistence.)"""
    mint: str
    entry_unix: int
    entry_price_usd: Decimal
    entry_sol_amount: int        # input amount in lamports
    received_tokens: int         # output amount in base units of the mint
    target_price_usd: Decimal    # absolute take-profit
    stop_price_usd: Decimal      # absolute hard stop
    peak_price_usd: Decimal      # for trailing
    trailing_pct: float = 0.5
    max_hold_seconds: int = 3600  # force exit after 1 hour if neither target/stop hits


@dataclass
class LiveRunnerConfig:
    """All the knobs in one place. Defaults are aggressive but bounded."""
    per_shot_sol: float = 0.05               # 0.05 SOL ≈ $10 per shot at SOL=$200
    max_concurrent_positions: int = 5         # never hold more than this many at once
    max_shots_per_hour: int = 30              # hard rate limit (filter rejects don't count)
    target_multiplier: float = 3.0            # exit at 3x
    stop_loss_pct: float = 0.50               # hard stop at -50%
    trailing_stop_pct: float = 0.50           # exit at 50% from peak after target zone
    quote_slippage_bps: int = 500             # 5% slippage tolerance on entry
    sandwich_protection: bool = True          # use Jito bundles when in live mode
    max_daily_loss_sol: float = 0.5           # hard kill at -0.5 SOL realized
    paper_mode_simulated_winrate: float = 0.0 # not used; outcomes come from real prices


@dataclass
class _RuntimeStats:
    shots_attempted: int = 0
    shots_filtered_out: int = 0
    shots_executed: int = 0
    shots_failed_swap: int = 0
    positions_closed_win: int = 0
    positions_closed_loss: int = 0
    realized_pnl_sol: float = 0.0
    shots_this_hour: list[float] = field(default_factory=list)


class A2LiveRunner:
    """The live A2 strategy execution loop."""

    def __init__(
        self,
        config: Optional[LiveRunnerConfig] = None,
        wallet: Optional[SolanaWallet] = None,
        enricher: Optional[SnapshotEnricher] = None,
        rug_filter: Optional[RugFilter] = None,
        router: Optional[JupiterRouter] = None,
    ) -> None:
        self.config = config or LiveRunnerConfig()
        # Default wallet: paper-mode observer if no env keys, otherwise from_env
        if wallet is None:
            try:
                wallet = SolanaWallet.from_env()
            except ValueError:
                wallet = SolanaWallet.observer("11111111111111111111111111111111")
        self.wallet = wallet
        self.enricher = enricher or SnapshotEnricher()
        self.rug = rug_filter or RugFilter()
        self.rpc = HeliusRPC()
        self.router = router or JupiterRouter(
            wallet=self.wallet, rpc=self.rpc,
            default_slippage_bps=self.config.quote_slippage_bps,
            use_jito=self.config.sandwich_protection,
        )
        self.jito = JitoBundle() if self.config.sandwich_protection else None
        self.open_positions: dict[str, LivePosition] = {}
        self.stats = _RuntimeStats()

    # ----- Public API -----

    async def run(self, use_websocket: bool = True) -> None:
        """The main loop. Streams new-pool events, evaluates, optionally enters."""
        log.info(
            "a2_live_runner_starting",
            mode=self.wallet.mode.value,
            use_ws=use_websocket,
            per_shot_sol=self.config.per_shot_sol,
            sandwich_protection=self.config.sandwich_protection,
        )

        producer = self._stream_via_websocket if use_websocket else self._stream_via_poller

        try:
            async for event in producer():
                # Two concurrent things to do on every tick:
                #   1) potentially enter a new position from this event
                #   2) update + maybe exit existing positions
                await asyncio.gather(
                    self._consider_entry(event),
                    self._sweep_exits(),
                    return_exceptions=True,
                )

                if self._daily_kill_triggered():
                    log.error("a2_daily_kill_triggered", realized_pnl_sol=self.stats.realized_pnl_sol)
                    break
        finally:
            await self._shutdown()

    # ----- Producer wiring -----

    async def _stream_via_websocket(self):
        async with HeliusWebSocket() as ws:
            async for event in ws.stream_new_pools():
                yield event

    async def _stream_via_poller(self):
        poller = HeliusNewPoolPoller()
        try:
            async for event in poller.stream_new_pools():
                yield event
        finally:
            await poller.close()

    # ----- Entry path -----

    async def _consider_entry(self, event: PoolCreationEvent) -> None:
        if len(self.open_positions) >= self.config.max_concurrent_positions:
            return
        if not self._within_rate_limit():
            return
        if event.mint_address in self.open_positions:
            return  # already in this token

        self.stats.shots_attempted += 1

        try:
            snap = await self.enricher.enrich(event.mint_address)
        except Exception as e:  # noqa: BLE001
            log.warning("enrich_failed_live", mint=event.mint_address, error=str(e))
            return
        if snap is None:
            return

        # For the live runner, we ALWAYS relax P02 (dev-history) since we don't
        # yet have the deployer-history indexer.
        if not snap.dev_history_known:
            from dataclasses import replace
            snap = replace(snap, dev_history_known=True, dev_rug_history_count=0)

        report = self.rug.check(snap)
        if not report.passed:
            self.stats.shots_filtered_out += 1
            return

        # Filter passed → enter
        await self._enter_position(snap)

    async def _enter_position(self, snap: TokenSnapshot) -> None:
        per_shot_lamports = int(self.config.per_shot_sol * 1_000_000_000)
        try:
            quote = await self.router.get_quote(
                input_mint=WSOL_MINT,
                output_mint=snap.mint_address,
                amount=per_shot_lamports,
                slippage_bps=self.config.quote_slippage_bps,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("a2_quote_failed", mint=snap.mint_address, error=str(e))
            self.stats.shots_failed_swap += 1
            return

        result = await self.router.swap(quote)
        if not result.success:
            self.stats.shots_failed_swap += 1
            log.info("a2_swap_failed", mint=snap.mint_address, error=result.error)
            self._write_fill_record(snap, quote, result, position=None, action="entry_failed")
            return

        self.stats.shots_executed += 1
        self.stats.shots_this_hour.append(time.time())
        entry_price = snap.last_trade_price_usd
        position = LivePosition(
            mint=snap.mint_address,
            entry_unix=int(time.time()),
            entry_price_usd=entry_price,
            entry_sol_amount=per_shot_lamports,
            received_tokens=result.out_amount,
            target_price_usd=entry_price * Decimal(self.config.target_multiplier),
            stop_price_usd=entry_price * Decimal(1.0 - self.config.stop_loss_pct),
            peak_price_usd=entry_price,
            trailing_pct=self.config.trailing_stop_pct,
        )
        self.open_positions[snap.mint_address] = position
        log.info(
            "a2_position_opened",
            mint=snap.mint_address[:8] + "...",
            entry=str(entry_price), target=str(position.target_price_usd),
            stop=str(position.stop_price_usd),
            mode=self.wallet.mode.value,
        )
        self._write_fill_record(snap, quote, result, position=position, action="entry")

    # ----- Exit path -----

    async def _sweep_exits(self) -> None:
        if not self.open_positions:
            return
        now = int(time.time())
        to_close: list[tuple[str, str]] = []  # (mint, reason)

        for mint, pos in list(self.open_positions.items()):
            # Pull current price via DexScreener-cached enrichment (lightweight)
            try:
                snap = await self.enricher.dex.fetch_token_snapshot(mint)
            except Exception:  # noqa: BLE001
                continue
            if snap is None:
                continue
            current = snap.last_trade_price_usd
            if current > pos.peak_price_usd:
                pos.peak_price_usd = current

            # Exit conditions
            if current <= pos.stop_price_usd:
                to_close.append((mint, "stop_loss"))
            elif current >= pos.target_price_usd:
                to_close.append((mint, "target"))
            elif current <= pos.peak_price_usd * Decimal(1.0 - pos.trailing_pct):
                to_close.append((mint, "trailing_stop"))
            elif now - pos.entry_unix >= pos.max_hold_seconds:
                to_close.append((mint, "time_exit"))

        for mint, reason in to_close:
            await self._close_position(mint, reason)

    async def _close_position(self, mint: str, reason: str) -> None:
        pos = self.open_positions.pop(mint, None)
        if pos is None:
            return
        # Swap token → SOL
        try:
            quote = await self.router.get_quote(
                input_mint=mint,
                output_mint=WSOL_MINT,
                amount=pos.received_tokens,
                slippage_bps=self.config.quote_slippage_bps,
            )
            result = await self.router.swap(quote)
        except Exception as e:  # noqa: BLE001
            log.warning("a2_close_quote_failed", mint=mint, error=str(e))
            return

        pnl_lamports = result.out_amount - pos.entry_sol_amount if result.success else -pos.entry_sol_amount
        pnl_sol = pnl_lamports / 1_000_000_000
        self.stats.realized_pnl_sol += pnl_sol
        if pnl_lamports >= 0:
            self.stats.positions_closed_win += 1
        else:
            self.stats.positions_closed_loss += 1

        log.info(
            "a2_position_closed",
            mint=mint[:8] + "...", reason=reason,
            pnl_sol=f"{pnl_sol:+.4f}",
            cum_pnl_sol=f"{self.stats.realized_pnl_sol:+.4f}",
        )
        # Synthesize a snapshot for the fill record
        from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot
        fake_snap = TokenSnapshot(
            mint_address=mint, symbol="?", name="?", venue_pair_address="",
            pool_age_seconds=int(time.time()) - pos.entry_unix,
            liquidity_usd=Decimal("0"), fully_diluted_value_usd=Decimal("0"),
            volume_5m_usd=Decimal("0"), volume_1h_usd=Decimal("0"),
            txns_5m=0, txns_1h=0,
            mint_authority_renounced=True, freeze_authority_renounced=True,
            lp_locked_or_burned=True, lp_lock_pct=1.0,
            top_10_holder_pct=0.0, dev_wallet_pct=0.0, n_holders=0,
            metadata_verified=False, dev_history_known=True, dev_rug_history_count=0,
            bid_ask_spread_pct=None,
            last_trade_price_usd=Decimal(str(quote.out_amount / max(quote.in_amount, 1) * 200)),  # rough USD
            snapshot_time=datetime.now(timezone.utc),
        )
        self._write_fill_record(fake_snap, quote, result, position=pos, action=f"exit_{reason}", pnl_sol=pnl_sol)

    # ----- Rate limiting / kill switches -----

    def _within_rate_limit(self) -> bool:
        now = time.time()
        self.stats.shots_this_hour = [t for t in self.stats.shots_this_hour if t > now - 3600]
        return len(self.stats.shots_this_hour) < self.config.max_shots_per_hour

    def _daily_kill_triggered(self) -> bool:
        return self.stats.realized_pnl_sol <= -abs(self.config.max_daily_loss_sol)

    # ----- Fill log -----

    def _write_fill_record(
        self,
        snap: TokenSnapshot,
        quote, result: SwapResult, position: Optional[LivePosition],
        action: str, pnl_sol: float = 0.0,
    ) -> None:
        parent = LIVE_FILLS_PATH.parent
        target = parent.resolve() if parent.is_symlink() else parent
        try:
            target.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
        record = {
            "action": action,
            "mode": result.mode,
            "timestamp_iso": datetime.now(timezone.utc).isoformat(),
            "mint": snap.mint_address,
            "symbol": snap.symbol,
            "in_amount": result.in_amount,
            "out_amount": result.out_amount,
            "realized_slippage_bps": result.realized_slippage_bps,
            "swap_success": result.success,
            "swap_error": result.error,
            "signature": result.signature,
            "position": asdict(position) if position is not None else None,
            "pnl_sol": pnl_sol,
            "cum_pnl_sol": self.stats.realized_pnl_sol,
        }
        with LIVE_FILLS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    async def _shutdown(self) -> None:
        # Close everything we own
        try:
            await self.enricher.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await self.router.close()
        except Exception:  # noqa: BLE001
            pass
        if self.jito:
            await self.jito.close()
        try:
            await self.rpc.close()
        except Exception:  # noqa: BLE001
            pass
        log.info(
            "a2_live_runner_done",
            shots_attempted=self.stats.shots_attempted,
            shots_executed=self.stats.shots_executed,
            wins=self.stats.positions_closed_win,
            losses=self.stats.positions_closed_loss,
            realized_pnl_sol=f"{self.stats.realized_pnl_sol:+.4f}",
        )
