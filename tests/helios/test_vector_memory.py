"""Tests for the pattern-memory vector store."""
from __future__ import annotations

from pathlib import Path

import pytest

from helios.memory.vector_store import PatternRecord, VectorMemory


def _rec(rid: str, vec: list[float], outcome: float, label: str = "win") -> PatternRecord:
    return PatternRecord(
        record_id=rid, strategy="A2",
        feature_vector=tuple(vec), feature_names=("a", "b", "c"),
        outcome_r=outcome, outcome_label=label, timestamp_unix=1000,
    )


@pytest.fixture
def mem(tmp_path) -> VectorMemory:
    return VectorMemory(path=tmp_path / "patterns.jsonl")


def test_empty_query_returns_empty(mem):
    assert mem.query([0.0, 0.0, 0.0]) == []


def test_add_and_persist(tmp_path):
    path = tmp_path / "p.jsonl"
    m1 = VectorMemory(path=path)
    m1.add(_rec("r1", [1.0, 0.0, 0.0], outcome=2.5))
    m1.add(_rec("r2", [0.0, 1.0, 0.0], outcome=-1.0, label="loss"))
    # Re-load fresh from disk → records survive
    m2 = VectorMemory(path=path)
    assert len(m2) == 2


def test_query_returns_nearest_first(mem):
    mem.add(_rec("a", [1.0, 0.0, 0.0], 2.0))
    mem.add(_rec("b", [0.0, 1.0, 0.0], -1.0))
    mem.add(_rec("c", [0.9, 0.1, 0.0], 1.5))
    results = mem.query([1.0, 0.0, 0.0], k=3)
    assert len(results) == 3
    assert results[0][1].record_id == "a"
    # Second-closest is "c" (very close to a)
    assert results[1][1].record_id == "c"


def test_similar_outcomes_summary(mem):
    # 5 wins (avg +2R), 5 losses (avg -1R)
    for i in range(5):
        mem.add(_rec(f"w{i}", [1.0 + i*0.01, 0.0, 0.0], 2.0))
    for i in range(5):
        mem.add(_rec(f"l{i}", [1.0 - i*0.01, 0.0, 0.0], -1.0, label="loss"))
    q = mem.similar_outcomes([1.0, 0.0, 0.0], k=10)
    assert q.n_neighbors == 10
    assert q.mean_outcome_r == pytest.approx(0.5)
    assert q.win_rate == pytest.approx(0.5)


def test_dim_mismatch_returns_empty(mem):
    mem.add(_rec("a", [1.0, 0.0, 0.0], 2.0))
    # Wrong dim
    assert mem.query([1.0, 0.0]) == []
