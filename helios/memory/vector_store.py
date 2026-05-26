"""Vector memory — JSONL-backed numpy-based pattern search.

Why not Qdrant/pgvector/Weaviate: at our scale (10k-100k observations), a
flat numpy cosine search is ~10ms per query and zero infra. We can swap to
a real vector DB once we have >1M observations or need sub-millisecond
latency — neither applies yet.

Schema:
    PatternRecord:
        record_id        unique
        strategy         which strategy generated this
        feature_vector   the model's pre-trade feature view (numeric)
        feature_names    parallel array of names (for audit)
        outcome_r        realized return in R-multiples (e.g. -1.0 = stop, +3 = 3x target)
        outcome_label    'win' | 'loss' | 'breakeven'
        context_metadata mint, ticker, etc.

Lookup:
    query(target_vec, k=20) → (similarity, record) pairs sorted desc
    similar_outcomes(target_vec, k=200) → summary stats over the nearest k
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean, median
from typing import Optional

import numpy as np

from helios.ops import get_logger

log = get_logger(__name__)

DEFAULT_VECTORS_PATH = Path(os.getenv("HELIOS_LOGS_DIR", "logs")) / "pattern_memory.jsonl"


@dataclass(frozen=True, slots=True)
class PatternRecord:
    record_id: str
    strategy: str
    feature_vector: tuple[float, ...]
    feature_names: tuple[str, ...]
    outcome_r: float                # realized return in R-multiples
    outcome_label: str              # 'win' | 'loss' | 'breakeven'
    timestamp_unix: int
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PatternQuery:
    """Summary of the k nearest historical setups."""
    n_neighbors: int
    mean_outcome_r: float
    median_outcome_r: float
    win_rate: float
    examples: list[PatternRecord]


class VectorMemory:
    """Append-only JSONL of pattern records + in-memory numpy index.

    Designed for the orchestrator to call `add()` after every closed trade
    and `query()` before every entry decision.
    """

    def __init__(self, path: Path | str = DEFAULT_VECTORS_PATH) -> None:
        self.path = Path(path)
        self._records: list[PatternRecord] = []
        self._vectors: Optional[np.ndarray] = None  # (n, d)
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._records.append(PatternRecord(
                    record_id=raw["record_id"],
                    strategy=raw["strategy"],
                    feature_vector=tuple(raw["feature_vector"]),
                    feature_names=tuple(raw["feature_names"]),
                    outcome_r=float(raw["outcome_r"]),
                    outcome_label=raw["outcome_label"],
                    timestamp_unix=int(raw["timestamp_unix"]),
                    metadata=raw.get("metadata", {}),
                ))
        self._rebuild_index()
        log.info("vector_memory_loaded", n=len(self._records))

    def _rebuild_index(self) -> None:
        if not self._records:
            self._vectors = None
            return
        self._vectors = np.array([r.feature_vector for r in self._records], dtype=np.float32)

    def add(self, record: PatternRecord) -> None:
        # Append to JSONL
        parent = self.path.parent
        target = parent.resolve() if parent.is_symlink() else parent
        try:
            target.mkdir(parents=True, exist_ok=True)
        except FileExistsError:
            pass
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), default=str) + "\n")
        self._records.append(record)
        # Cheap incremental: append to in-memory array
        vec = np.array(record.feature_vector, dtype=np.float32).reshape(1, -1)
        self._vectors = vec if self._vectors is None else np.vstack([self._vectors, vec])

    def query(self, target_vec: np.ndarray | list[float], k: int = 20) -> list[tuple[float, PatternRecord]]:
        """Return the k nearest records by cosine similarity, sorted desc."""
        if self._vectors is None or len(self._records) == 0:
            return []
        target = np.array(target_vec, dtype=np.float32).reshape(1, -1)
        if target.shape[1] != self._vectors.shape[1]:
            log.warning("vector_dim_mismatch", got=target.shape[1], expected=self._vectors.shape[1])
            return []
        # Cosine similarity
        a_norm = self._vectors / np.maximum(np.linalg.norm(self._vectors, axis=1, keepdims=True), 1e-9)
        t_norm = target / np.maximum(np.linalg.norm(target, axis=1, keepdims=True), 1e-9)
        sims = (a_norm @ t_norm.T).flatten()
        # Top-k
        k = min(k, len(sims))
        idx = np.argpartition(-sims, k - 1)[:k]
        idx_sorted = idx[np.argsort(-sims[idx])]
        return [(float(sims[i]), self._records[i]) for i in idx_sorted]

    def similar_outcomes(self, target_vec: np.ndarray | list[float], k: int = 200) -> PatternQuery:
        """Aggregate stats over the k nearest historical records.

        Use this RIGHT before making an entry decision: "I'm about to take a
        setup that looks like X — what happened the last 200 times this shape
        appeared?"
        """
        neighbors = self.query(target_vec, k)
        if not neighbors:
            return PatternQuery(0, 0.0, 0.0, 0.0, [])
        outcomes = [n[1].outcome_r for n in neighbors]
        wins = sum(1 for r in outcomes if r > 0)
        return PatternQuery(
            n_neighbors=len(outcomes),
            mean_outcome_r=mean(outcomes),
            median_outcome_r=median(outcomes),
            win_rate=wins / len(outcomes),
            examples=[n[1] for n in neighbors[:5]],
        )

    def __len__(self) -> int:
        return len(self._records)
