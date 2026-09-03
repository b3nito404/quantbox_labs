"""Construction and statistical analysis of spreads between two assets.

This is the core of statistical arbitrage research: identifying pairs of assets
whose price relationship has been historically stable, in order to trade the mean
reversion of that relationship when it deviates abnormally.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint


@dataclass
class CointegrationResult:
    """Result of a cointegration test between two price series."""

    p_value: float
    test_statistic: float
    hedge_ratio: float

    @property
    def is_cointegrated(self, threshold: float = 0.05) -> bool:
        """True if the p value is below the threshold, 5 percent by default.

        A low p value is a necessary but not sufficient condition. It does not
        replace out of sample validation.
        """
        return self.p_value < threshold


def hedge_ratio(price_a: pd.Series, price_b: pd.Series) -> float:
    """Compute the hedge ratio through simple linear regression.

    The spread is then defined as: spread = price_a - hedge_ratio * price_b
    """
    covariance = np.cov(price_a, price_b)[0, 1]
    variance_b = np.var(price_b)
    return float(covariance / variance_b)


def check_cointegration(price_a: pd.Series, price_b: pd.Series) -> CointegrationResult:
    """Test whether two price series are cointegrated using the Engle Granger test.

    A low p value suggests a stable long term relationship between the two assets,
    a baseline condition for a mean reversion strategy on the spread to make
    statistical sense.
    """
    test_statistic, p_value, _ = coint(price_a, price_b)
    ratio = hedge_ratio(price_a, price_b)
    return CointegrationResult(p_value=p_value, test_statistic=test_statistic, hedge_ratio=ratio)


def build_spread(price_a: pd.Series, price_b: pd.Series, ratio: float | None = None) -> pd.Series:
    """Build the spread series between two assets, aligned on the same time index."""
    if ratio is None:
        ratio = hedge_ratio(price_a, price_b)
    return price_a - ratio * price_b


def zscore(series: pd.Series, window: int = 30) -> pd.Series:
    """Compute the rolling zscore of a series, used as an entry and exit signal.

    Using a rolling window, rather than statistics computed over the full period,
    avoids using future information to judge a present point, a necessary condition
    to avoid look ahead bias.
    """
    rolling_mean = series.rolling(window=window).mean()
    rolling_std = series.rolling(window=window).std()
    return (series - rolling_mean) / rolling_std


def half_life_mean_reversion(spread: pd.Series) -> float:
    """Estimate the half life of mean reversion of the spread, in number of periods.

    A very long, negative, or infinite half life signals a spread that does not
    reliably revert to its mean within an exploitable horizon, a warning sign that
    should not be ignored.
    """
    spread_lag = spread.shift(1)
    spread_diff = spread - spread_lag
    valid = spread_lag.notna() & spread_diff.notna()

    x = spread_lag[valid].to_numpy()
    y = spread_diff[valid].to_numpy()
    x_mean, y_mean = x.mean(), y.mean()
    lam = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)

    if lam >= 0:
        return float("inf")  # no mean reversion detected
    return float(-np.log(2) / lam)
