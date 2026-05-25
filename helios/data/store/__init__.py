"""Parquet + DuckDB analytic store. Every dataset partitioned by date.

Layout on disk:
    {root}/{dataset}/year={Y}/month={M}/day={D}/part-{uuid}.parquet

Every row carries `event_time` (when it happened in the market) AND
`available_at` (when our system could first have seen it). The PIT layer in
helios.data.pit refuses to return rows where `available_at > as_of`.
"""
from helios.data.store.parquet_store import ParquetStore

__all__ = ["ParquetStore"]
