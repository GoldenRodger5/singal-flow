"""Drift monitor — KS test + PSI on feature distributions over time.

When a strategy's input feature distribution shifts (regime change, new bot
behavior, exchange policy change), models trained on the old distribution
silently lose edge. The drift monitor catches this BEFORE realized P&L
collapses. Standard quant hygiene.

Two metrics:
  KS  Kolmogorov-Smirnov D-statistic between two empirical distributions.
      Threshold: > 0.2 = significant shift.
  PSI Population Stability Index. Distribution-shape divergence over fixed
      buckets. Threshold: > 0.25 = significant shift (industry standard).

Usage:
    monitor = DriftMonitor(reference_window=baseline_features)
    status = monitor.check(current_window=last_24h_features)
    if status.is_drifted:
        bench_strategy()
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True, slots=True)
class DriftStatus:
    feature_name: str
    ks_statistic: float
    psi_score: float
    is_drifted: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class DriftReport:
    overall_drifted: bool
    feature_statuses: tuple[DriftStatus, ...]
    n_features_drifted: int


class DriftMonitor:
    def __init__(
        self,
        ks_threshold: float = 0.2,
        psi_threshold: float = 0.25,
        n_buckets: int = 10,
    ) -> None:
        self.ks_threshold = ks_threshold
        self.psi_threshold = psi_threshold
        self.n_buckets = n_buckets

    def check_feature(self, name: str, baseline: np.ndarray, current: np.ndarray) -> DriftStatus:
        baseline = np.asarray(baseline, dtype=float)
        current = np.asarray(current, dtype=float)
        baseline = baseline[~np.isnan(baseline)]
        current = current[~np.isnan(current)]
        if len(baseline) < 30 or len(current) < 30:
            return DriftStatus(
                feature_name=name, ks_statistic=0.0, psi_score=0.0,
                is_drifted=False, reason="insufficient_samples",
            )

        # KS
        ks_stat, _ = stats.ks_2samp(baseline, current)

        # PSI: bucket on baseline quantiles, compare densities
        try:
            edges = np.quantile(baseline, np.linspace(0, 1, self.n_buckets + 1))
            edges[0] = -np.inf
            edges[-1] = np.inf
            baseline_hist, _ = np.histogram(baseline, bins=edges)
            current_hist, _ = np.histogram(current, bins=edges)
            baseline_pct = baseline_hist / max(baseline_hist.sum(), 1)
            current_pct = current_hist / max(current_hist.sum(), 1)
            # Avoid zeros
            baseline_pct = np.where(baseline_pct == 0, 1e-6, baseline_pct)
            current_pct = np.where(current_pct == 0, 1e-6, current_pct)
            psi = float(np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct)))
        except Exception:  # noqa: BLE001
            psi = 0.0

        drifted = ks_stat > self.ks_threshold or psi > self.psi_threshold
        reason = ""
        if drifted:
            parts = []
            if ks_stat > self.ks_threshold:
                parts.append(f"ks={ks_stat:.2f}")
            if psi > self.psi_threshold:
                parts.append(f"psi={psi:.2f}")
            reason = " ".join(parts)

        return DriftStatus(
            feature_name=name, ks_statistic=float(ks_stat),
            psi_score=float(psi), is_drifted=drifted, reason=reason,
        )

    def check_many(
        self, baseline_by_feature: dict[str, np.ndarray], current_by_feature: dict[str, np.ndarray]
    ) -> DriftReport:
        statuses: list[DriftStatus] = []
        for name, baseline in baseline_by_feature.items():
            if name not in current_by_feature:
                continue
            statuses.append(self.check_feature(name, baseline, current_by_feature[name]))
        n_drifted = sum(1 for s in statuses if s.is_drifted)
        return DriftReport(
            overall_drifted=n_drifted > 0,
            feature_statuses=tuple(statuses),
            n_features_drifted=n_drifted,
        )
