"""Convert list[Bar] -> Polars frame in the schema feature pipelines expect.

The features.py modules consume a Polars DataFrame with columns:
    symbol, event_time, available_at, open, high, low, close, volume

This helper centralizes the conversion so adapter outputs flow cleanly into
feature pipelines without each strategy reinventing the wheel.
"""
from __future__ import annotations

import polars as pl

from helios.data.adapters import Bar
from helios.data.adapters.kraken_futures import FundingRecord


def bars_to_frame(bars: list[Bar]) -> pl.DataFrame:
    if not bars:
        return pl.DataFrame(schema={
            "symbol": pl.Utf8,
            "event_time": pl.Datetime("us", "UTC"),
            "available_at": pl.Datetime("us", "UTC"),
            "open": pl.Float64, "high": pl.Float64, "low": pl.Float64, "close": pl.Float64,
            "volume": pl.Float64,
        })
    rows = [{
        "symbol": b.symbol,
        "event_time": b.event_time,
        "available_at": b.available_at,
        "open": float(b.open),
        "high": float(b.high),
        "low": float(b.low),
        "close": float(b.close),
        "volume": float(b.volume),
    } for b in bars]
    return pl.from_dicts(rows).with_columns([
        pl.col("event_time").cast(pl.Datetime("us", "UTC")),
        pl.col("available_at").cast(pl.Datetime("us", "UTC")),
    ]).sort(["symbol", "event_time"])


def funding_to_frame(records: list[FundingRecord]) -> pl.DataFrame:
    if not records:
        return pl.DataFrame(schema={
            "symbol": pl.Utf8,
            "event_time": pl.Datetime("us", "UTC"),
            "available_at": pl.Datetime("us", "UTC"),
            "funding_rate": pl.Float64,
        })
    rows = [{
        "symbol": r.symbol,
        "event_time": r.event_time,
        "available_at": r.available_at,
        "funding_rate": r.funding_rate,
    } for r in records]
    return pl.from_dicts(rows).with_columns([
        pl.col("event_time").cast(pl.Datetime("us", "UTC")),
        pl.col("available_at").cast(pl.Datetime("us", "UTC")),
    ]).sort(["symbol", "event_time"])


def align_funding_to_bars(bars: pl.DataFrame, funding: pl.DataFrame) -> pl.DataFrame:
    """Asof-join funding onto bars so each bar carries the most-recent
    funding-rate observation available at that time. PIT-correct: only past
    funding observations attach to a bar.
    """
    if funding.height == 0:
        return bars.with_columns(pl.lit(None, dtype=pl.Float64).alias("funding_rate"))
    return bars.sort("event_time").join_asof(
        funding.sort("event_time").select(["symbol", "event_time", "funding_rate"]),
        on="event_time",
        by="symbol",
        strategy="backward",
    )
