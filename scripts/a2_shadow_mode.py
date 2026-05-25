"""A2 shadow-mode runner — fetches a complete enriched TokenSnapshot for each
candidate mint, applies the RugFilter, prints the decision and reason codes.

Usage:
  python -m scripts.a2_shadow_mode --candidates <mint1> <mint2> ...
  python -m scripts.a2_shadow_mode --trending           # pulls from DexScreener trending
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import httpx
from dotenv import load_dotenv

from helios.ops import configure_logging, get_logger
from helios.strategies.a2_meme_snipe import RugFilter
from helios.strategies.a2_meme_snipe.enricher import SnapshotEnricher
from helios.strategies.a2_meme_snipe.log import write_observation
from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot

load_dotenv()
log = get_logger("a2_shadow")


def print_snapshot(snap: TokenSnapshot) -> None:
    print(f"\n  Mint:        {snap.mint_address}")
    print(f"  Symbol/Name: {snap.symbol} / {snap.name}")
    age_min, age_sec = divmod(snap.pool_age_seconds, 60)
    age_hr, age_min = divmod(age_min, 60)
    print(f"  Pool age:    {age_hr}h {age_min}m {age_sec}s")
    print(f"  Liquidity:   ${snap.liquidity_usd:,.0f}")
    print(f"  FDV:         ${snap.fully_diluted_value_usd:,.0f}")
    print(f"  Vol 5m/1h:   ${snap.volume_5m_usd:,.0f} / ${snap.volume_1h_usd:,.0f}")
    print(f"  Txns 5m/1h:  {snap.txns_5m} / {snap.txns_1h}")
    print(f"  Price:       ${snap.last_trade_price_usd}")
    print(f"  Authorities: mint_renounced={snap.mint_authority_renounced}  "
          f"freeze_renounced={snap.freeze_authority_renounced}  "
          f"lp_locked≈{snap.lp_locked_or_burned} ({snap.lp_lock_pct:.0%})")
    print(f"  Concentration: top10={snap.top_10_holder_pct:.2%}  "
          f"top1≈dev={snap.dev_wallet_pct:.2%}  holders_reported={snap.n_holders}")
    print(f"  Provenance:  metadata={snap.metadata_verified}  "
          f"dev_known={snap.dev_history_known}  prior_rugs={snap.dev_rug_history_count}")


async def fetch_trending_solana(limit: int = 10) -> list[str]:
    """DexScreener's latest token profiles — used as a free way to find currently
    traded Solana tokens for shadow-mode evaluation."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get("https://api.dexscreener.com/token-profiles/latest/v1")
        resp.raise_for_status()
        profiles = resp.json()
        mints = [
            p["tokenAddress"]
            for p in profiles
            if p.get("chainId") == "solana" and p.get("tokenAddress")
        ]
        return mints[:limit]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", nargs="+", default=[])
    parser.add_argument("--trending", action="store_true",
                        help="Pull recent Solana token profiles from DexScreener")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--relaxed-only-K", action="store_true",
                        help="Also report decisions if only K-bucket (authorities) is enforced")
    parser.add_argument("--shadow-relax-p02", action="store_true",
                        help="Treat tokens as if dev_history were known (for shadow-mode study only)")
    parser.add_argument("--log", action="store_true",
                        help="Persist each observation to logs/a2_shadow.jsonl for later outcome harvest")
    args = parser.parse_args()

    configure_logging(level="WARNING")

    mints: list[str] = list(args.candidates)
    if args.trending or not mints:
        print("Pulling recent Solana token profiles from DexScreener...")
        mints = (mints + await fetch_trending_solana(args.limit))[: args.limit]
        print(f"Got {len(mints)} candidate mints")

    if not mints:
        print("No mints to evaluate. Pass --candidates or --trending.")
        return 0

    enricher = SnapshotEnricher()
    rug = RugFilter()

    pass_count = 0
    reject_count = 0
    reject_codes: dict[str, int] = {}

    try:
        print("\n" + "=" * 70)
        print(f"{'A2 SHADOW MODE — live filter on ' + str(len(mints)) + ' candidates':^70}")
        print("=" * 70)
        for i, mint in enumerate(mints):
            if i > 0:
                # Birdeye free tier ~1 req/sec; back off to be safe across calls
                await asyncio.sleep(1.1)
            try:
                snap = await enricher.enrich(mint)
            except Exception as e:  # noqa: BLE001
                print(f"\n  {mint}: ENRICH FAILED — {e}")
                continue
            if snap is None:
                print(f"\n  {mint}: not found")
                continue

            # Optional: synthesize a "known good dev" version of the snapshot for
            # shadow-mode learning. Useful before the dev-history indexer is built.
            if args.shadow_relax_p02 and not snap.dev_history_known:
                from dataclasses import replace
                snap = replace(snap, dev_history_known=True, dev_rug_history_count=0)

            print_snapshot(snap)
            report = rug.check(snap)
            if report.passed:
                pass_count += 1
                print(f"  ==> FILTER PASS — would shadow-log entry at ${snap.last_trade_price_usd}")
            else:
                reject_count += 1
                print(f"  ==> FILTER REJECT ({len(report.reasons)} reason{'s' if len(report.reasons) > 1 else ''})")
                for code in report.reasons:
                    short = code.split("_")[0]
                    reject_codes[short] = reject_codes.get(short, 0) + 1
                    print(f"     - {code}")

            if args.log:
                obs_id = write_observation(
                    snap,
                    filter_decision=report.decision.value,
                    filter_reasons=list(report.reasons),
                )
                print(f"  logged obs_id={obs_id[:8]}...")
    finally:
        await enricher.close()

    print("\n" + "=" * 70)
    print(f"{'SUMMARY':^70}")
    print("=" * 70)
    print(f"Total evaluated:  {pass_count + reject_count}")
    print(f"Passed filter:    {pass_count}")
    print(f"Rejected:         {reject_count}")
    if reject_codes:
        print("\nRejection breakdown by check code:")
        for code, n in sorted(reject_codes.items(), key=lambda x: -x[1]):
            print(f"  {code}*: {n} hits")
    print("\nKey for codes: K=authorities  L=liquidity  C=concentration  P=provenance  M=microstructure")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
