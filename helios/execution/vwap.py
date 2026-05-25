"""VWAP child-order schedule. Deterministic baseline.

The RL execution agent (Phase 4) is benchmarked against this. Promotion to
live requires beating it by >= 15 bps on a held-out fill set.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ChildOrder:
    slice_index: int
    qty: Decimal
    delay_seconds: float


def vwap_schedule(
    total_qty: Decimal,
    n_slices: int,
    volume_profile: list[float],
    spread_seconds: float = 60.0,
) -> list[ChildOrder]:
    """Split total_qty into n_slices weighted by the volume_profile.

    volume_profile is a list of expected relative volume per slice (any units,
    will be normalized). Slices are evenly spaced in time by `spread_seconds`.
    """
    if n_slices < 1:
        raise ValueError("n_slices must be >= 1")
    if len(volume_profile) != n_slices:
        raise ValueError(f"volume_profile must have {n_slices} entries; got {len(volume_profile)}")
    if any(v < 0 for v in volume_profile):
        raise ValueError("volume_profile entries must be non-negative")

    total_weight = sum(volume_profile)
    if total_weight <= 0:
        # Uniform fallback
        weights = [1.0 / n_slices] * n_slices
    else:
        weights = [v / total_weight for v in volume_profile]

    schedule: list[ChildOrder] = []
    cumulative = Decimal("0")
    for i, w in enumerate(weights):
        slice_qty = total_qty * Decimal(str(w))
        if i == n_slices - 1:
            # Last slice eats any rounding residue so the total is exact
            slice_qty = total_qty - cumulative
        cumulative += slice_qty
        schedule.append(ChildOrder(
            slice_index=i,
            qty=slice_qty,
            delay_seconds=i * spread_seconds,
        ))
    return schedule
