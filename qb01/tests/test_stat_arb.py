"""Tests for quantbox.strategies.stat_arb, pure signal logic, no backtest."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantbox.strategies.stat_arb import Signal, StatArbConfig, generate_signals


def _make_series(values: list[float]) -> pd.Series:
    index = pd.date_range("2024-01-01", periods=len(values), freq="h")
    return pd.Series(values, index=index)


def test_generate_signals_stays_flat_without_extreme_zscore():
    # Two identical series produce a constant spread, so the zscore is always NaN
    # or zero, and a signal should never trigger
    price_a = _make_series([100.0] * 50)
    price_b = _make_series([50.0] * 50)

    result = generate_signals(
        price_a, price_b, hedge_ratio=2.0, config=StatArbConfig(zscore_window=10)
    )

    assert (result["signal"] == Signal.FLAT).all()


def test_generate_signals_enters_position_on_extreme_deviation():
    rng = np.random.default_rng(0)
    n = 100
    # Stable spread followed by a large one time upward shock
    base = list(rng.normal(0, 0.1, n))
    price_b = _make_series([100.0] * n)
    price_a_values = [100.0 + b for b in base]
    price_a_values[70] += 20  # sudden shock, the zscore should become extreme here
    price_a = _make_series(price_a_values)

    result = generate_signals(
        price_a,
        price_b,
        hedge_ratio=1.0,
        config=StatArbConfig(zscore_window=20, entry_threshold=2.0),
    )

    # At or just after the shock, the signal should no longer be FLAT
    assert (result["signal"].iloc[69:71] != Signal.FLAT).any()


def test_generate_signals_exits_when_spread_reverts():
    rng = np.random.default_rng(1)
    n = 150
    base = list(rng.normal(0, 0.1, n))
    price_b = _make_series([100.0] * n)
    price_a_values = [100.0 + b for b in base]
    # Shock followed by an immediate return to the normal regime
    price_a_values[70] += 20
    for i in range(71, 100):
        price_a_values[i] = 100.0 + base[i]
    price_a = _make_series(price_a_values)

    result = generate_signals(
        price_a,
        price_b,
        hedge_ratio=1.0,
        config=StatArbConfig(zscore_window=20, entry_threshold=2.0, exit_threshold=0.5),
    )

    # Well after the return to normal, the position should be back to FLAT
    assert result["signal"].iloc[-1] == Signal.FLAT
