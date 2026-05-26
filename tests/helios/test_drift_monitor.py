"""Tests for the drift monitor."""
from __future__ import annotations

import numpy as np

from helios.models.drift import DriftMonitor


def test_no_drift_on_identical_distributions():
    np.random.seed(0)
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(0, 1, 1000)
    m = DriftMonitor()
    s = m.check_feature("x", baseline, current)
    assert not s.is_drifted


def test_drift_detected_on_mean_shift():
    np.random.seed(0)
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(2.0, 1, 1000)  # mean shifted by 2 sigma
    m = DriftMonitor()
    s = m.check_feature("x", baseline, current)
    assert s.is_drifted
    assert s.ks_statistic > 0.2


def test_drift_detected_on_variance_change():
    np.random.seed(0)
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(0, 3.0, 1000)  # 3x variance
    m = DriftMonitor()
    s = m.check_feature("x", baseline, current)
    assert s.is_drifted


def test_insufficient_samples_no_drift_decision():
    baseline = np.array([1.0, 2.0, 3.0])
    current = np.array([10.0, 20.0])
    m = DriftMonitor()
    s = m.check_feature("x", baseline, current)
    assert not s.is_drifted
    assert s.reason == "insufficient_samples"


def test_check_many_aggregates():
    np.random.seed(0)
    baseline = {
        "stable": np.random.normal(0, 1, 1000),
        "shifted": np.random.normal(0, 1, 1000),
    }
    current = {
        "stable": np.random.normal(0, 1, 1000),
        "shifted": np.random.normal(3.0, 1, 1000),
    }
    m = DriftMonitor()
    r = m.check_many(baseline, current)
    assert r.overall_drifted
    assert r.n_features_drifted == 1
    drifted_names = [s.feature_name for s in r.feature_statuses if s.is_drifted]
    assert drifted_names == ["shifted"]
