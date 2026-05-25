"""Split-conformal prediction. Distribution-free, finite-sample calibrated
prediction intervals.

The contract:
  Given a base model that produces point predictions ŷ for inputs x, and a
  held-out calibration set (x_cal, y_cal), the SplitConformal object exposes:

      lower(yhat, alpha) -> float
      upper(yhat, alpha) -> float
      interval(yhat, alpha) -> (lo, hi)

  such that across the calibration distribution, the true y falls within
  [lower, upper] with marginal probability >= 1 - alpha.

This is what powers the "the bot refuses to trade when it doesn't know"
property: position size is computed off `lower(yhat, alpha)`, so a wide
interval shrinks size automatically — and a negative lower bound zeros it
out entirely (see helios.sizing.kelly).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SplitConformal:
    """Symmetric split-conformal residual calibrator.

    Fit on (predictions, actuals) from a held-out set; expose calibrated
    one-sided lower/upper bounds at the desired alpha.
    """

    residuals: np.ndarray  # |y - yhat| on the calibration set

    @classmethod
    def fit(cls, y_pred: np.ndarray, y_true: np.ndarray) -> SplitConformal:
        if y_pred.shape != y_true.shape:
            raise ValueError(f"Shape mismatch: {y_pred.shape} vs {y_true.shape}")
        if len(y_pred) < 30:
            raise ValueError(f"Need >= 30 calibration samples; got {len(y_pred)}")
        residuals = np.abs(y_true - y_pred)
        return cls(residuals=residuals)

    def quantile(self, alpha: float) -> float:
        """Return the (1 - alpha) quantile of absolute residuals, with the
        finite-sample correction `ceil((n+1)*(1-alpha)) / n`."""
        if not 0.0 < alpha < 1.0:
            raise ValueError("alpha must be in (0, 1)")
        n = len(self.residuals)
        k = int(np.ceil((n + 1) * (1.0 - alpha)))
        k = min(k, n)
        q = np.sort(self.residuals)[k - 1]
        return float(q)

    def lower(self, y_pred: float, alpha: float = 0.1) -> float:
        return float(y_pred - self.quantile(alpha))

    def upper(self, y_pred: float, alpha: float = 0.1) -> float:
        return float(y_pred + self.quantile(alpha))

    def interval(self, y_pred: float, alpha: float = 0.1) -> tuple[float, float]:
        q = self.quantile(alpha)
        return (float(y_pred - q), float(y_pred + q))
