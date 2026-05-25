"""A1 feature pipeline. Pure functions on a Polars DataFrame.

Every feature is point-in-time correct: it uses only bars whose
`available_at` is <= the row's `available_at`. The data plane's PIT guard
ensures the input frame is already filtered; this module only computes.
"""
from __future__ import annotations

import polars as pl

# Names of features this module produces, in stable order. Used by the model
# loader as a schema check and by audit logging.
FEATURE_NAMES: tuple[str, ...] = (
    "ret_1",
    "ret_5",
    "ret_20",
    "vol_20",
    "vol_zscore_20_vs_60",
    "momentum_zscore_20",
    "volume_ratio_5_vs_60",
    "funding_zscore_24",
    "oi_change_pct_24",
)


def compute_features(bars: pl.DataFrame) -> pl.DataFrame:
    """Compute the A1 feature set.

    Expected `bars` schema (post-PIT, post-funding-merge):
        symbol, event_time, available_at, open, high, low, close, volume,
        funding_rate (nullable — null entries are fine, rolling stats handle it)

    Returns a frame with FEATURE_NAMES columns plus (symbol, event_time, available_at).
    """
    if bars.height == 0:
        return bars.with_columns([pl.lit(None).alias(name) for name in FEATURE_NAMES])

    df = bars.sort(["symbol", "event_time"])

    df = df.with_columns([
        pl.col("close").pct_change().over("symbol").alias("ret_1"),
    ])
    df = df.with_columns([
        (pl.col("close") / pl.col("close").shift(5).over("symbol") - 1.0).alias("ret_5"),
        (pl.col("close") / pl.col("close").shift(20).over("symbol") - 1.0).alias("ret_20"),
        pl.col("ret_1").rolling_std(window_size=20).over("symbol").alias("vol_20"),
        pl.col("volume").rolling_mean(window_size=5).over("symbol").alias("_vol5"),
        pl.col("volume").rolling_mean(window_size=60).over("symbol").alias("_vol60"),
    ])
    df = df.with_columns([
        (pl.col("_vol5") / pl.col("_vol60")).alias("volume_ratio_5_vs_60"),
        (pl.col("vol_20") / pl.col("ret_1").rolling_std(window_size=60).over("symbol"))
        .alias("vol_zscore_20_vs_60"),
        (pl.col("ret_1").rolling_mean(window_size=20).over("symbol")
         / pl.col("vol_20")).alias("momentum_zscore_20"),
    ])

    if "funding_rate" in df.columns:
        df = df.with_columns([
            pl.col("funding_rate").rolling_mean(window_size=24).over("symbol").alias("_fr_mean24"),
            pl.col("funding_rate").rolling_std(window_size=24).over("symbol").alias("_fr_std24"),
        ]).with_columns([
            ((pl.col("funding_rate") - pl.col("_fr_mean24")) / pl.col("_fr_std24"))
            .alias("funding_zscore_24"),
        ])
    else:
        df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("funding_zscore_24"))

    # OI feature: placeholder until OI adapter ships; null for now.
    df = df.with_columns(pl.lit(None).cast(pl.Float64).alias("oi_change_pct_24"))

    keep = ["symbol", "event_time", "available_at", *FEATURE_NAMES]
    return df.select(keep)
