"""A1 training pipeline.

Inputs:  Polars DataFrame of computed features (helios.strategies.a1_perp_trend.features)
         plus a label column (forward N-bar return sign).
Process: walk-forward XGBoost training; per-fold predictions; conformal
         calibration on the held-out portion of each fold; deflated Sharpe
         on the OOS strategy returns.
Output:  TrainResult(model, calibrator, tearsheet, feature_importances)

The pipeline is deterministic given a fixed random_state. Reproducibility is
table stakes — we log the model + calibrator + feature manifest to MLflow and
key audit-log entries off the artifact hash.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl  # noqa: F401  (used by placeholder check)

from helios.backtest.tearsheet import TearSheet, tearsheet
from helios.backtest.walkforward import walk_forward_splits
from helios.models import SplitConformal
from helios.ops import get_logger
from helios.strategies.a1_perp_trend.features import FEATURE_NAMES

log = get_logger(__name__)


@dataclass
class TrainResult:
    feature_importances: dict[str, float]
    calibrator: SplitConformal
    oos_returns: np.ndarray
    oos_tearsheet: TearSheet
    threshold: float
    n_trades: int = 0
    trade_hit_rate: float = 0.0
    # Cost-aware diagnostics
    n_transitions: float = 0.0
    gross_return_mean: float = 0.0
    cost_drag_per_bar_bps: float = 0.0


def evaluate_signal(
    oos_pred: np.ndarray,
    fwd_ret: np.ndarray,
    vol_20: np.ndarray | None = None,
    threshold: float = 0.55,
    cost_bps_per_fill: float = 6.0,
    target_vol_per_bar: float | None = None,
    max_vol_leverage: float = 3.0,
) -> tuple[np.ndarray, dict[str, float]]:
    """Convert OOS predictions into a net-of-cost strategy return series.

    For each bar t:
      pos_t = +1 if pred_t > threshold; -1 if pred_t < (1-threshold); else 0.
      Optional vol-target: pos_t *= clip(target_vol / vol_20_t, 0.1, max_vol_leverage)
      net_ret_t = pos_t * fwd_ret_t  -  |pos_t - pos_{t-1}| * (cost_bps_per_fill / 1e4)

    Assumes 1-bar holding period (so fwd_ret_t is the t->t+1 return).
    """
    long_mask = oos_pred > threshold
    short_mask = oos_pred < (1.0 - threshold)
    pos = np.where(long_mask, 1.0, np.where(short_mask, -1.0, 0.0))

    if target_vol_per_bar is not None and vol_20 is not None:
        with np.errstate(divide="ignore", invalid="ignore"):
            scale = target_vol_per_bar / np.maximum(vol_20, 1e-6)
        scale = np.clip(scale, 0.1, max_vol_leverage)
        scale = np.nan_to_num(scale, nan=0.0)
        pos = pos * scale

    raw_ret = pos * fwd_ret

    pos_prev = np.concatenate(([0.0], pos[:-1]))
    transitions = np.abs(pos - pos_prev)
    cost = transitions * (cost_bps_per_fill / 10000.0)

    net_ret = raw_ret - cost

    return net_ret, {
        "n_position_bars": float(np.count_nonzero(np.abs(pos) > 0)),
        "n_transitions": float(transitions.sum()),
        "gross_return_mean": float(raw_ret.mean()),
        "cost_drag_per_bar_bps": float(cost.mean() * 10000),
    }


def make_labels(df: pl.DataFrame, horizon: int = 4) -> pl.DataFrame:
    """Forward N-bar return label: +1 if forward return > 0, else 0.

    The horizon (in bars) is the holding period the model is trained to
    predict. For A1 on hourly bars, horizon=4 = 4-hour forward return.
    """
    df = df.sort(["symbol", "event_time"])
    df = df.with_columns([
        (pl.col("close").shift(-horizon).over("symbol") / pl.col("close") - 1.0).alias("fwd_ret"),
    ])
    df = df.with_columns([
        (pl.col("fwd_ret") > 0).cast(pl.Int32).alias("y"),
    ])
    return df


def train_a1(
    feat_df: pl.DataFrame,
    horizon: int = 4,
    n_splits: int = 5,
    val_size: int = 200,
    min_train_size: int = 500,
    n_trials: int = 1,
    random_state: int = 0,
    apply_costs: bool = True,
    cost_bps_per_fill: float = 6.0,
    target_vol_per_bar: float | None = None,
) -> TrainResult:
    """Walk-forward train a gradient-boosted classifier on the A1 feature set.

    Returns OOS metrics and a fitted conformal calibrator on aggregated OOS
    predictions.
    """
    try:
        import xgboost as xgb
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "xgboost is required for training. Install via `pip install xgboost`."
        ) from e

    df = make_labels(feat_df, horizon=horizon)
    # Fill placeholder-null feature columns (funding/OI before those adapters exist) with 0
    placeholder_cols = [c for c in FEATURE_NAMES if df.select(pl.col(c).is_null().all()).item()]
    if placeholder_cols:
        df = df.with_columns([pl.col(c).fill_null(0.0) for c in placeholder_cols])
    # CRITICAL: sort by time globally (NOT by symbol then time) so walk-forward
    # splits the array along the time axis. Without this, splits leak symbol-by-symbol
    # and walk-forward stops being walk-forward.
    df = df.drop_nulls(subset=["y", *FEATURE_NAMES, "fwd_ret"]).sort("event_time")
    X = df.select(list(FEATURE_NAMES)).to_numpy()
    y = df.select("y").to_numpy().ravel()
    fwd_ret = df.select("fwd_ret").to_numpy().ravel()
    vol_20 = df.select("vol_20").to_numpy().ravel() if "vol_20" in df.columns else None

    if len(X) < min_train_size + n_splits * val_size:
        raise ValueError(
            f"Insufficient data for walk-forward: have {len(X)}, "
            f"need >= {min_train_size + n_splits * val_size}"
        )

    splits = walk_forward_splits(
        n_samples=len(X), n_splits=n_splits, val_size=val_size, min_train_size=min_train_size
    )

    all_oos_pred: list[float] = []
    all_oos_y: list[int] = []
    all_oos_ret: list[float] = []
    all_oos_vol: list[float] = []
    importances_accum: dict[str, float] = {f: 0.0 for f in FEATURE_NAMES}

    final_model = None
    for split in splits:
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=random_state,
            eval_metric="logloss",
            tree_method="hist",
            verbosity=0,
        )
        model.fit(X[split.train_idx], y[split.train_idx])
        pred = model.predict_proba(X[split.val_idx])[:, 1]
        all_oos_pred.extend(pred.tolist())
        all_oos_y.extend(y[split.val_idx].tolist())
        all_oos_ret.extend(fwd_ret[split.val_idx].tolist())
        if vol_20 is not None:
            all_oos_vol.extend(vol_20[split.val_idx].tolist())
        for fname, imp in zip(FEATURE_NAMES, model.feature_importances_, strict=False):
            importances_accum[fname] += float(imp)
        final_model = model

    oos_pred = np.array(all_oos_pred)
    oos_y = np.array(all_oos_y)
    oos_ret = np.array(all_oos_ret)
    oos_vol = np.array(all_oos_vol) if all_oos_vol else None

    # Conformal calibration on |predicted_prob - realized_y|. We treat the
    # classifier's probability as a proxy for expected forward return sign;
    # the calibrator gives us a lower bound for the sizing layer to consume.
    calibrator = SplitConformal.fit(oos_pred, oos_y.astype(float))

    # Strategy OOS returns: cost-aware, optionally vol-targeted.
    # Long when pred > threshold; short when pred < (1 - threshold); flat otherwise.
    # Holding 1 bar so fwd_ret_t is the t->t+1 return.
    threshold = 0.55
    strat_ret, diagnostics = evaluate_signal(
        oos_pred=oos_pred,
        fwd_ret=oos_ret,
        vol_20=oos_vol,
        threshold=threshold,
        cost_bps_per_fill=cost_bps_per_fill if apply_costs else 0.0,
        target_vol_per_bar=target_vol_per_bar,
    )
    ts = tearsheet(strat_ret, periods_per_year=365 * 24, n_trials=n_trials)

    # Trade-level hit rate (only count bars where we actually had a position)
    long_mask = oos_pred > threshold
    short_mask = oos_pred < (1.0 - threshold)
    traded_mask = long_mask | short_mask
    if traded_mask.any():
        gross_per_trade = np.where(long_mask, oos_ret, np.where(short_mask, -oos_ret, 0.0))
        trade_hit_rate = float((gross_per_trade[traded_mask] > 0).sum() / traded_mask.sum())
    else:
        trade_hit_rate = 0.0
    n_trades = int(traded_mask.sum())

    # Normalize aggregated importances
    total = sum(importances_accum.values()) or 1.0
    importances = {k: v / total for k, v in importances_accum.items()}

    log.info(
        "a1_train_done",
        n_samples=len(X),
        n_folds=len(splits),
        n_trades=n_trades,
        trade_hit_rate=trade_hit_rate,
        oos_sharpe=ts.sharpe,
        oos_dd=ts.max_drawdown,
        deflated=ts.deflated_sharpe,
        threshold=threshold,
    )

    return TrainResult(
        feature_importances=importances,
        calibrator=calibrator,
        oos_returns=strat_ret,
        oos_tearsheet=ts,
        threshold=threshold,
        n_trades=n_trades,
        trade_hit_rate=trade_hit_rate,
        n_transitions=diagnostics["n_transitions"],
        gross_return_mean=diagnostics["gross_return_mean"],
        cost_drag_per_bar_bps=diagnostics["cost_drag_per_bar_bps"],
    )


def train_a1_cross_symbol(
    feat_df: pl.DataFrame,
    train_symbols: list[str],
    test_symbols: list[str],
    horizon: int = 1,
    random_state: int = 0,
    apply_costs: bool = True,
    cost_bps_per_fill: float = 6.0,
    target_vol_per_bar: float | None = None,
) -> TrainResult:
    """Train on `train_symbols`, test on `test_symbols`. Time-split too: the
    train window is the older half, test is the newer half, so the test is
    BOTH cross-symbol AND time out-of-sample.

    This is the cleanest generalization test: if the signal only worked because
    it overfit to symbol-specific quirks, this collapses.
    """
    try:
        import xgboost as xgb
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("xgboost required") from e

    df = make_labels(feat_df, horizon=horizon)
    placeholder_cols = [c for c in FEATURE_NAMES if df.select(pl.col(c).is_null().all()).item()]
    if placeholder_cols:
        df = df.with_columns([pl.col(c).fill_null(0.0) for c in placeholder_cols])
    df = df.drop_nulls(subset=["y", *FEATURE_NAMES, "fwd_ret"]).sort("event_time")

    # Split time at median event_time so train is older, test is newer.
    # Use a UTC-aware Python datetime literal to match the column's timezone.
    from datetime import datetime as _dt
    from datetime import timezone as _tz
    times_ns = df.select(pl.col("event_time").cast(pl.Int64)).to_numpy().ravel()
    t_split_ns = int(np.percentile(times_ns, 50))
    # Polars int64 of Datetime("us") is microseconds since epoch
    t_split_dt = _dt.fromtimestamp(t_split_ns / 1_000_000, tz=_tz.utc)

    train_df = df.filter(
        (pl.col("symbol").is_in(train_symbols))
        & (pl.col("event_time") < pl.lit(t_split_dt).cast(pl.Datetime("us", "UTC")))
    )
    test_df = df.filter(
        (pl.col("symbol").is_in(test_symbols))
        & (pl.col("event_time") >= pl.lit(t_split_dt).cast(pl.Datetime("us", "UTC")))
    )

    if train_df.height < 500 or test_df.height < 100:
        raise ValueError(
            f"Insufficient data: train={train_df.height} rows on {train_symbols}, "
            f"test={test_df.height} rows on {test_symbols}"
        )

    X_tr = train_df.select(list(FEATURE_NAMES)).to_numpy()
    y_tr = train_df.select("y").to_numpy().ravel()
    X_te = test_df.select(list(FEATURE_NAMES)).to_numpy()
    y_te = test_df.select("y").to_numpy().ravel()
    fwd_ret_te = test_df.select("fwd_ret").to_numpy().ravel()
    vol_20_te = test_df.select("vol_20").to_numpy().ravel() if "vol_20" in test_df.columns else None

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        random_state=random_state, eval_metric="logloss",
        tree_method="hist", verbosity=0,
    )
    model.fit(X_tr, y_tr)
    pred = model.predict_proba(X_te)[:, 1]

    threshold = 0.55
    strat_ret, diag = evaluate_signal(
        oos_pred=pred,
        fwd_ret=fwd_ret_te,
        vol_20=vol_20_te,
        threshold=threshold,
        cost_bps_per_fill=cost_bps_per_fill if apply_costs else 0.0,
        target_vol_per_bar=target_vol_per_bar,
    )
    ts = tearsheet(strat_ret, periods_per_year=365 * 24, n_trials=1)

    long_mask = pred > threshold
    short_mask = pred < (1.0 - threshold)
    traded_mask = long_mask | short_mask
    gross = np.where(long_mask, fwd_ret_te, np.where(short_mask, -fwd_ret_te, 0.0))
    hit_rate = float((gross[traded_mask] > 0).sum() / traded_mask.sum()) if traded_mask.any() else 0.0

    importances = {f: float(v) for f, v in zip(FEATURE_NAMES, model.feature_importances_, strict=False)}
    total_imp = sum(importances.values()) or 1.0
    importances = {k: v / total_imp for k, v in importances.items()}

    calibrator = SplitConformal.fit(pred, y_te.astype(float))

    log.info(
        "a1_cross_symbol_done",
        train_symbols=train_symbols, test_symbols=test_symbols,
        train_rows=train_df.height, test_rows=test_df.height,
        sharpe=ts.sharpe, max_dd=ts.max_drawdown, hit_rate=hit_rate, n_trades=int(traded_mask.sum()),
    )

    return TrainResult(
        feature_importances=importances,
        calibrator=calibrator,
        oos_returns=strat_ret,
        oos_tearsheet=ts,
        threshold=threshold,
        n_trades=int(traded_mask.sum()),
        trade_hit_rate=hit_rate,
        n_transitions=diag["n_transitions"],
        gross_return_mean=diag["gross_return_mean"],
        cost_drag_per_bar_bps=diag["cost_drag_per_bar_bps"],
    )
