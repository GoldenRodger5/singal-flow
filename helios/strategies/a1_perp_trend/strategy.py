"""A1 Strategy class. Glues feature pipeline + model + conformal calibration
into the Strategy ABC interface.

Phase 2 scope: skeleton with deterministic placeholder model. Real XGBoost
training + walk-forward validation arrives in the next iteration once the
data plane is populated.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from helios.strategies.base import Strategy, StrategyContext
from helios.types import Signal, StrategyId, Venue


@dataclass
class A1Config:
    model_path: Path | None = None
    confidence_threshold: float = 0.55
    conformal_lower_floor: float = 0.005  # require >= 0.5% expected return lower bound
    leverage: float = 3.0


class A1PerpTrend(Strategy):
    id = StrategyId.A1_PERP_TREND
    feature_manifest = (
        "ret_1", "ret_5", "ret_20", "vol_20",
        "vol_zscore_20_vs_60", "momentum_zscore_20",
        "volume_ratio_5_vs_60", "funding_zscore_24", "oi_change_pct_24",
    )

    def __init__(self, config: A1Config | None = None) -> None:
        self.config = config or A1Config()
        self._model = None  # loaded in prepare()
        self._calibrator = None

    async def prepare(self) -> None:
        # TODO Phase 2: load XGBoost artifact + conformal calibrator from MLflow registry.
        # For now: prepared = ready-to-receive-evaluations, with a deterministic stub model.
        self._model = _StubModel()
        self._calibrator = _StubCalibrator()

    async def evaluate(self, ctx: StrategyContext) -> list[Signal]:
        if self._model is None:
            raise RuntimeError("A1PerpTrend.prepare() must be called before evaluate()")

        # In Phase 2 this branch pulls features for ctx.universe at ctx.as_of via PIT layer,
        # runs the XGBoost model, calibrates with conformal, and emits Signals.
        # For the skeleton we emit nothing — the strategy is wired but silent until model loads.
        _ = ctx  # placeholder
        return []

    @staticmethod
    def _features_hash(values: tuple[float, ...]) -> str:
        h = hashlib.sha256()
        for v in values:
            h.update(str(v).encode())
        return h.hexdigest()[:16]


class _StubModel:
    """Placeholder until XGBoost training pipeline (next iteration) replaces this."""
    def predict_proba(self, _features: list[float]) -> float:
        return 0.5


class _StubCalibrator:
    def lower_bound(self, _p: float) -> float:
        return 0.0
