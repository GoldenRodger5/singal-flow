"""Shadow-log writer / reader. Append-only JSONL files.

logs/a2_shadow.jsonl   — one record per detection event:
    {obs_id, mint, timestamp_iso, filter_decision, filter_reasons, snapshot}

logs/a2_outcomes.jsonl — one record per harvested outcome:
    {obs_id, mint, entry_unix, entry_price, window_label, outcome_metrics}

The harvester keys outcomes back to observations via obs_id. Idempotent: an
obs_id present in outcomes.jsonl is skipped on re-harvest.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from helios.strategies.a2_meme_snipe.snapshot import TokenSnapshot

# Default log paths. In Railway with a /data volume mount, HELIOS_LOGS_DIR
# should be set to /data/logs (set automatically in the Dockerfile). Locally
# (no env var) defaults to ./logs for tests and dev.
import os as _os
_LOGS_DIR = _os.getenv("HELIOS_LOGS_DIR", "logs")
SHADOW_LOG_DEFAULT = Path(_LOGS_DIR) / "a2_shadow.jsonl"
OUTCOMES_LOG_DEFAULT = Path(_LOGS_DIR) / "a2_outcomes.jsonl"


def _json_default(o: Any) -> Any:
    if isinstance(o, Decimal):
        return str(o)
    if isinstance(o, datetime):
        return o.isoformat()
    if is_dataclass(o):
        return asdict(o)
    raise TypeError(f"Not serializable: {type(o)}")


def _ensure_dir(path: Path) -> None:
    parent = path.parent
    # Follow dangling symlinks (e.g. /app/logs -> /data/logs after volume mount)
    target = parent.resolve() if parent.is_symlink() else parent
    try:
        target.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass


def write_observation(
    snap: TokenSnapshot,
    filter_decision: str,
    filter_reasons: list[str],
    path: Path = SHADOW_LOG_DEFAULT,
) -> str:
    """Append one observation to the shadow log. Returns the generated obs_id."""
    _ensure_dir(path)
    obs_id = str(uuid.uuid4())
    record = {
        "obs_id": obs_id,
        "mint": snap.mint_address,
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "filter_decision": filter_decision,
        "filter_reasons": list(filter_reasons),
        "snapshot": snap,  # _json_default handles dataclass + Decimal
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=_json_default) + "\n")
    return obs_id


def read_observations(path: Path = SHADOW_LOG_DEFAULT) -> Iterable[dict]:
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def write_outcome(record: dict, path: Path = OUTCOMES_LOG_DEFAULT) -> None:
    _ensure_dir(path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=_json_default) + "\n")


def read_outcomes(path: Path = OUTCOMES_LOG_DEFAULT) -> Iterable[dict]:
    if not path.exists():
        return []
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def harvested_obs_ids(path: Path = OUTCOMES_LOG_DEFAULT) -> set[str]:
    return {r["obs_id"] for r in read_outcomes(path) if "obs_id" in r}
