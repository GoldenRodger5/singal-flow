"""Performance metrics. Pure functions over a returns array.

Why Deflated Sharpe Ratio: when you search over many strategies/hyperparams,
the best in-sample Sharpe is inflated by selection bias. DSR ([Bailey & López
de Prado 2014]) penalizes the headline Sharpe by the number of trials.
A backtest with DSR > 0 has > 50% probability that the true Sharpe is > 0.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True, slots=True)
class TearSheet:
    n_periods: int
    total_return: float
    cagr: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    hit_rate: float
    win_loss_ratio: float
    deflated_sharpe: float | None  # filled in when n_trials provided


def _annualization_factor(periods_per_year: int) -> float:
    return math.sqrt(periods_per_year)


def sharpe(returns: np.ndarray, periods_per_year: int = 252, rf: float = 0.0) -> float:
    if len(returns) == 0:
        return 0.0
    excess = returns - rf / periods_per_year
    std = excess.std(ddof=1) if len(excess) > 1 else 0.0
    if std == 0:
        return 0.0
    return float(excess.mean() / std * _annualization_factor(periods_per_year))


def sortino(returns: np.ndarray, periods_per_year: int = 252, rf: float = 0.0) -> float:
    if len(returns) == 0:
        return 0.0
    excess = returns - rf / periods_per_year
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float("inf") if excess.mean() > 0 else 0.0
    dd_std = downside.std(ddof=1) if len(downside) > 1 else 0.0
    if dd_std == 0:
        return 0.0
    return float(excess.mean() / dd_std * _annualization_factor(periods_per_year))


def max_drawdown(returns: np.ndarray) -> float:
    """Returns the worst peak-to-trough drawdown as a non-negative fraction."""
    if len(returns) == 0:
        return 0.0
    equity = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / peak
    return float(dd.max())


def hit_rate(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    wins = (returns > 0).sum()
    return float(wins / len(returns))


def win_loss_ratio(returns: np.ndarray) -> float:
    if len(returns) == 0:
        return 0.0
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    if len(wins) == 0 or len(losses) == 0:
        return 0.0
    return float(wins.mean() / abs(losses.mean()))


def deflated_sharpe(
    observed_sr: float,
    returns: np.ndarray,
    n_trials: int,
    periods_per_year: int = 252,
) -> float:
    """Deflated Sharpe Ratio. Returns the probability that the TRUE Sharpe > 0
    given the observed Sharpe came from `n_trials` independent trials.

    A DSR < 0.95 (i.e. < 95% confident) is normally treated as 'not robust'.
    """
    if len(returns) < 4 or n_trials < 1:
        return 0.0
    # Sample skew/kurtosis of the underlying returns
    skew = float(stats.skew(returns))
    kurt = float(stats.kurtosis(returns, fisher=True))  # excess kurtosis
    n = len(returns)

    # Expected max SR across n_trials independent Sharpe samples ~ N(0, 1/sqrt(n))
    # Approximation from Bailey & López de Prado:
    emc = 0.5772156649  # Euler-Mascheroni
    z = (1 - emc) * stats.norm.ppf(1 - 1.0 / n_trials) + emc * stats.norm.ppf(1 - 1.0 / (n_trials * math.e))
    expected_max_sr = z * (1.0 / math.sqrt(n))

    sr_annual_to_period = observed_sr / math.sqrt(periods_per_year)
    numerator = (sr_annual_to_period - expected_max_sr) * math.sqrt(n - 1)
    denominator = math.sqrt(1 - skew * sr_annual_to_period + ((kurt) / 4.0) * sr_annual_to_period ** 2)
    if denominator <= 0:
        return 0.0
    dsr = stats.norm.cdf(numerator / denominator)
    return float(dsr)


def tearsheet(
    returns: np.ndarray,
    periods_per_year: int = 252,
    n_trials: int | None = None,
) -> TearSheet:
    if len(returns) == 0:
        return TearSheet(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None)
    total = float(np.prod(1.0 + returns) - 1.0)
    n = len(returns)
    cagr = float((1.0 + total) ** (periods_per_year / n) - 1.0) if total > -1 else -1.0
    sr = sharpe(returns, periods_per_year)
    so = sortino(returns, periods_per_year)
    mdd = max_drawdown(returns)
    cal = cagr / mdd if mdd > 0 else 0.0
    hr = hit_rate(returns)
    wlr = win_loss_ratio(returns)
    dsr = deflated_sharpe(sr, returns, n_trials, periods_per_year) if n_trials else None
    return TearSheet(
        n_periods=n,
        total_return=total,
        cagr=cagr,
        sharpe=sr,
        sortino=so,
        max_drawdown=mdd,
        calmar=cal,
        hit_rate=hr,
        win_loss_ratio=wlr,
        deflated_sharpe=dsr,
    )
