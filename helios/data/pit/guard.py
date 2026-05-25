"""Point-in-time query guard.

Usage:
    table = as_of_query(store, "SELECT * FROM bars_1m WHERE symbol = 'BTC-USD'", as_of=t)

Behavior:
  - Each dataset is registered as a view with a built-in `available_at <= ?`
    filter.
  - If the query result contains any row with `available_at > as_of`, raise
    PITViolation.

This double-check is intentional belt-and-suspenders. The view filter is the
primary defense; the post-query assertion is the canary that catches schema
drift or a user bypassing the helper.
"""
from __future__ import annotations

from datetime import datetime

import duckdb
import pyarrow as pa

from helios.data.store import ParquetStore


class PITViolation(RuntimeError):
    """A row that postdates the as_of timestamp leaked into a result. Capital risk."""


def as_of_query(store: ParquetStore, sql: str, as_of: datetime) -> pa.Table:
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")

    for ds_dir in store.root.iterdir():
        if not ds_dir.is_dir():
            continue
        glob = str(ds_dir / "**" / "*.parquet")
        # Inject PIT filter at the view level — any query against `ds.name`
        # only ever sees rows with available_at <= as_of.
        con.execute(
            f"""
            CREATE VIEW {ds_dir.name} AS
            SELECT * FROM read_parquet('{glob}', hive_partitioning=true)
            WHERE available_at <= TIMESTAMP '{as_of.isoformat()}'
            """
        )

    _arrow = con.execute(sql).arrow()
    result = _arrow.read_all() if hasattr(_arrow, "read_all") else _arrow

    # Canary: if the user joined external data or otherwise bypassed the view,
    # we still catch leaks here.
    if "available_at" in result.column_names and result.num_rows > 0:
        max_avail = max(result.column("available_at").to_pylist())
        # Normalize tz
        if max_avail.tzinfo is None:
            max_avail = max_avail.replace(tzinfo=as_of.tzinfo)
        if max_avail > as_of:
            raise PITViolation(
                f"Result row with available_at={max_avail.isoformat()} > as_of={as_of.isoformat()}"
            )

    return result
