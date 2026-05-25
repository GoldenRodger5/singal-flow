"""Tests for split-conformal calibration."""
from __future__ import annotations

import numpy as np
import pytest

from helios.models.conformal import SplitConformal


def test_fit_requires_min_samples():
    with pytest.raises(ValueError):
        SplitConformal.fit(np.zeros(10), np.zeros(10))


def test_coverage_holds_marginally():
    """Across the calibration distribution, the true y should land in
    [lower, upper] with probability ~ 1 - alpha. We check via a held-out
    test set drawn from the same distribution.
    """
    rng = np.random.default_rng(0)
    n_cal, n_test = 500, 500

    # Simple regression: y = 2x + noise. Base model predicts 2x exactly.
    x_cal = rng.normal(0, 1, n_cal)
    y_cal = 2 * x_cal + rng.normal(0, 1, n_cal)
    yhat_cal = 2 * x_cal

    cal = SplitConformal.fit(yhat_cal, y_cal)

    x_test = rng.normal(0, 1, n_test)
    y_test = 2 * x_test + rng.normal(0, 1, n_test)
    yhat_test = 2 * x_test

    alpha = 0.1
    coverage = 0
    for yt, yh in zip(y_test, yhat_test, strict=False):
        lo, hi = cal.interval(float(yh), alpha)
        if lo <= yt <= hi:
            coverage += 1
    rate = coverage / n_test
    # Conformal guarantee: rate >= 1 - alpha asymptotically (here ~0.9)
    assert rate >= 0.85, f"Coverage {rate} too low"


def test_lower_below_pred_upper_above():
    rng = np.random.default_rng(1)
    yhat = rng.normal(0, 1, 100)
    y = yhat + rng.normal(0, 0.5, 100)
    cal = SplitConformal.fit(yhat, y)
    pred = 1.5
    lo = cal.lower(pred)
    hi = cal.upper(pred)
    assert lo < pred < hi


def test_alpha_out_of_range_raises():
    cal = SplitConformal.fit(np.zeros(50), np.ones(50) * 0.5)
    with pytest.raises(ValueError):
        cal.quantile(0.0)
    with pytest.raises(ValueError):
        cal.quantile(1.0)
