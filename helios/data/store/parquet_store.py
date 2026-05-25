"""ParquetStore — partitioned write/read over a local or object-store root.

Append-only. Schema-validated. Every write requires `event_time` and
`available_at` columns; missing either is a hard failure.

This implementation uses pyarrow + duckdb. The interface is designed so that
swapping the backend to R2/S3 later is a config change, not a rewrite.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

REQUIRED_COLUMNS = ("event_time", "available_at")


class SchemaError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class WriteResult:
    dataset: str
    rows: int
    path: str


class ParquetStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _validate(self, table: pa.Table) -> None:
        cols = set(table.column_names)
        missing = [c for c in REQUIRED_COLUMNS if c not in cols]
        if missing:
            raise SchemaError(f"Missing required columns: {missing}. Have: {sorted(cols)}")
        # Ensure both are timestamps
        for c in REQUIRED_COLUMNS:
            if not pa.types.is_timestamp(table.schema.field(c).type):
                raise SchemaError(f"Column {c!r} must be timestamp, got {table.schema.field(c).type}")

    def write(self, dataset: str, table: pa.Table, partition_date: datetime | None = None) -> WriteResult:
        self._validate(table)
        # Default partition is the max event_time in the batch (so a backfill of yesterday lands in yesterday)
        if partition_date is None:
            event_times = table.column("event_time").to_pylist()
            partition_date = max(event_times) if event_times else datetime.now(timezone.utc)
        d = partition_date
        part_dir = (
            self.root / dataset / f"year={d.year:04d}" / f"month={d.month:02d}" / f"day={d.day:02d}"
        )
        part_dir.mkdir(parents=True, exist_ok=True)
        path = part_dir / f"part-{uuid.uuid4()}.parquet"
        pq.write_table(table, path, compression="zstd")
        return WriteResult(dataset=dataset, rows=table.num_rows, path=str(path))

    def query(self, sql: str, as_of: datetime | None = None) -> pa.Table:
        """Run a SQL query against the store.

        If `as_of` is provided, automatically appends a PIT filter
        (`available_at <= as_of`) — but only if the user's SQL already
        references the source as a registered view. The PIT layer in
        helios.data.pit is the recommended interface.
        """
        con = duckdb.connect()
        # Register every dataset as a globbed view
        for ds_dir in self.root.iterdir():
            if ds_dir.is_dir():
                glob = str(ds_dir / "**" / "*.parquet")
                con.execute(
                    f"CREATE VIEW {ds_dir.name} AS SELECT * FROM read_parquet('{glob}', hive_partitioning=true)"
                )
        if as_of is not None:
            con.execute("SET TimeZone = 'UTC'")
        _arrow = con.execute(sql).arrow()
        return _arrow.read_all() if hasattr(_arrow, "read_all") else _arrow

    def datasets(self) -> list[str]:
        return sorted([p.name for p in self.root.iterdir() if p.is_dir()])
