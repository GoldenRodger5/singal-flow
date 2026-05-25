"""Tests for walk-forward + purged k-fold."""
from __future__ import annotations

import numpy as np
import pytest

from helios.backtest.walkforward import (
    assert_no_overlap,
    purged_kfold,
    walk_forward_splits,
)


def test_walk_forward_basic_no_overlap():
    splits = walk_forward_splits(n_samples=100, n_splits=4, val_size=10, min_train_size=60)
    assert len(splits) == 4
    assert_no_overlap(splits)


def test_walk_forward_train_grows():
    splits = walk_forward_splits(n_samples=200, n_splits=5, val_size=20, min_train_size=80)
    for i in range(1, len(splits)):
        assert len(splits[i].train_idx) > len(splits[i - 1].train_idx)


def test_walk_forward_train_always_before_val():
    splits = walk_forward_splits(n_samples=200, n_splits=5, val_size=20, min_train_size=80)
    for s in splits:
        assert s.train_idx.max() < s.val_idx.min()


def test_walk_forward_insufficient_samples():
    with pytest.raises(ValueError):
        walk_forward_splits(n_samples=50, n_splits=5, val_size=20, min_train_size=80)


def test_purged_kfold_partitions_val_indices():
    n = 100
    splits = purged_kfold(n_samples=n, n_splits=5, embargo=0)
    all_val = np.concatenate([s.val_idx for s in splits])
    assert np.array_equal(np.sort(all_val), np.arange(n))


def test_purged_kfold_embargo_excludes_train_around_val():
    splits = purged_kfold(n_samples=100, n_splits=5, embargo=3)
    for s in splits:
        # No train index should land in [val_start - embargo, val_end + embargo)
        val_start, val_end = s.val_idx.min(), s.val_idx.max() + 1
        embargoed = set(range(max(0, val_start - 3), min(100, val_end + 3)))
        assert not embargoed.intersection(s.train_idx.tolist())


def test_purged_kfold_no_train_val_overlap():
    splits = purged_kfold(n_samples=200, n_splits=10, embargo=5)
    assert_no_overlap(splits)
