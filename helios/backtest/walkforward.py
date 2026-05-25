"""Walk-forward and purged cross-validation splits.

walk_forward_splits():
    Rolling expanding-train / fixed-val. Produces N (train, val) index pairs.

purged_kfold():
    Lopez de Prado purged k-fold. Adds an `embargo` gap so that any sample
    whose label depends on the future cannot leak from train into val.

These are pure functions over index arrays. No I/O.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Split:
    train_idx: np.ndarray
    val_idx: np.ndarray
    fold: int


def walk_forward_splits(
    n_samples: int,
    n_splits: int,
    val_size: int,
    min_train_size: int = 0,
) -> list[Split]:
    """Expanding-window walk-forward. The val window slides forward by `val_size`
    each fold; the train window grows.

        |==train==|val|
        |====train====|val|
        |======train======|val|
    """
    if n_splits < 1:
        raise ValueError("n_splits must be >= 1")
    if val_size < 1:
        raise ValueError("val_size must be >= 1")

    total_needed = min_train_size + n_splits * val_size
    if total_needed > n_samples:
        raise ValueError(
            f"Need {total_needed} samples for {n_splits} splits "
            f"with val_size={val_size} and min_train_size={min_train_size}; have {n_samples}"
        )

    splits: list[Split] = []
    train_end = max(min_train_size, n_samples - n_splits * val_size)
    for k in range(n_splits):
        val_start = train_end
        val_end = val_start + val_size
        if val_end > n_samples:
            break
        train_idx = np.arange(0, val_start)
        val_idx = np.arange(val_start, val_end)
        splits.append(Split(train_idx=train_idx, val_idx=val_idx, fold=k))
        train_end = val_end
    return splits


def purged_kfold(
    n_samples: int,
    n_splits: int,
    embargo: int = 0,
) -> list[Split]:
    """Purged k-fold. Each sample appears in exactly one val fold. Train fold
    excludes the val window AND an embargo gap on either side.

    The embargo defends against label leakage when the label of sample i
    depends on bars after i.
    """
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")
    if embargo < 0:
        raise ValueError("embargo must be >= 0")

    fold_size = n_samples // n_splits
    if fold_size < 1:
        raise ValueError("Not enough samples for that many folds")

    splits: list[Split] = []
    for k in range(n_splits):
        val_start = k * fold_size
        val_end = (k + 1) * fold_size if k < n_splits - 1 else n_samples
        val_idx = np.arange(val_start, val_end)

        # Train = everything NOT in [val_start - embargo, val_end + embargo)
        purge_start = max(0, val_start - embargo)
        purge_end = min(n_samples, val_end + embargo)
        mask = np.ones(n_samples, dtype=bool)
        mask[purge_start:purge_end] = False
        train_idx = np.where(mask)[0]
        splits.append(Split(train_idx=train_idx, val_idx=val_idx, fold=k))
    return splits


def assert_no_overlap(splits: Iterable[Split]) -> None:
    """Sanity check: train and val never share an index in any fold."""
    for s in splits:
        common = np.intersect1d(s.train_idx, s.val_idx)
        if len(common) > 0:
            raise AssertionError(f"Fold {s.fold} has train/val overlap: {common[:5]}...")
