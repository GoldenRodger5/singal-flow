"""Model layer — pure-Python wrappers and calibrators that wrap concrete ML
artifacts (XGBoost, sklearn) loaded from the MLflow registry.

Conformal calibration is the prime contribution of this package: every model's
point prediction is paired with a calibrated lower bound on expected return,
and that lower bound is what the sizer (helios.sizing.kelly) actually reads.
"""
from helios.models.conformal import SplitConformal

__all__ = ["SplitConformal"]
