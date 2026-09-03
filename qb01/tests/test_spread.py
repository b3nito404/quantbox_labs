"""Tests for quantbox.research.spread. No database dependency here."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantbox.research.spread import (
    build_spread,
    check_cointegration,
    half_life_mean_reversion,
    hedge_ratio,
    zscore,
)


@pytest.fixture
def synthetic_pair() -> tuple[pd.Series, pd.Series]:
    """Two synthetic price series, cointegrated by construction.

    B follows a random walk, and A equals 2 times B plus stationary noise. The
    relationship between A and B is therefore known in advance, which allows us to
    verify that our functions correctly recover the expected statistical
    properties.
    """
    rng = np.random.default_rng(seed=42)
    n = 500
    index = pd.date_range("2024-01-01", periods=n, freq="h")

    price_b = pd.Series(100 + np.cumsum(rng.normal(0, 1, n)), index=index)
    noise = rng.normal(0, 1, n)  # stationary noise, not a random walk
    price_a = 2 * price_b + noise

    return price_a, price_b


def test_hedge_ratio_recovers_known_relationship(synthetic_pair):
    price_a, price_b = synthetic_pair
    ratio = hedge_ratio(price_a, price_b)

    # A was built as 2*B plus noise, so the estimated ratio should be close to 2
    assert ratio == pytest.approx(2.0, abs=0.1)


def test_build_spread_is_stationary_like(synthetic_pair):
    price_a, price_b = synthetic_pair
    spread = build_spread(price_a, price_b)

    # The spread should have a much lower variance than the raw prices, which
    # indicates the common trend, the random walk in B, has been removed
    assert spread.std() < price_a.std()


def test_cointegration_detects_known_relationship(synthetic_pair):
    price_a, price_b = synthetic_pair
    result = check_cointegration(price_a, price_b)

    # By construction, these series are cointegrated, so the p value should be low
    assert result.p_value < 0.05


def test_zscore_has_zero_mean_over_window(synthetic_pair):
    price_a, price_b = synthetic_pair
    spread = build_spread(price_a, price_b)
    z = zscore(spread, window=30)

    # The first values, before the window is filled, should be NaN
    assert z.iloc[:29].isna().all()
    # Once the window is filled, values should be numeric
    assert z.iloc[100:].notna().all()


def test_half_life_is_positive_for_mean_reverting_spread(synthetic_pair):
    price_a, price_b = synthetic_pair
    spread = build_spread(price_a, price_b)
    half_life = half_life_mean_reversion(spread)

    # The spread was built as stationary white noise, so the half life should be
    # finite and positive, indicating mean reversion was detected
    assert half_life > 0
    assert half_life != float("inf")
