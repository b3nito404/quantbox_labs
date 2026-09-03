"""Statistical arbitrage strategy, the first strategy of QuantBox Labs.

Principle: when the spread between two cointegrated assets deviates abnormally from
its recent mean, expressed as a high zscore, the strategy bets on mean reversion.

    zscore above entry_threshold:   spread abnormally high, short A, long B
    zscore below negative entry_threshold: spread abnormally low, long A, short B
    absolute zscore below exit_threshold:  spread back near its mean, close position

This module only generates a signal. It does not simulate or execute any order.
That responsibility belongs to the backtest engine, quantbox.backtest.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import pandas as pd

from quantbox.research.spread import build_spread, zscore


class Signal(IntEnum):
    """Target position at a given time, from the perspective of asset A."""

    FLAT = 0
    LONG_A_SHORT_B = 1
    SHORT_A_LONG_B = -1


@dataclass
class StatArbConfig:
    """Parameters of the statistical arbitrage strategy."""

    zscore_window: int = 30
    entry_threshold: float = 2.0
    exit_threshold: float = 0.5


def generate_signals(
    price_a: pd.Series,
    price_b: pd.Series,
    hedge_ratio: float,
    config: StatArbConfig | None = None,
) -> pd.DataFrame:
    """Generate the signal series, target position, for the pair (A, B).

    The hedge ratio should be computed on a training period distinct from the
    period used to generate signals, to avoid leaking future information into the
    past.

    Returns a DataFrame with columns: spread, zscore, signal.
    """
    config = config or StatArbConfig()

    spread = build_spread(price_a, price_b, ratio=hedge_ratio)
    z = zscore(spread, window=config.zscore_window)

    signal = pd.Series(Signal.FLAT, index=z.index, dtype=int)
    position = Signal.FLAT

    # Explicit loop, not vectorized, on purpose: the position depends on the
    # previous state, since entry and exit do not happen at the same instant based
    # on a single threshold check, which makes a purely vectorized implementation
    # risky to get right on the first attempt.
    for i, current_z in enumerate(z):
        if pd.isna(current_z):
            signal.iloc[i] = Signal.FLAT
            continue

        if position == Signal.FLAT:
            if current_z > config.entry_threshold:
                position = Signal.SHORT_A_LONG_B
            elif current_z < -config.entry_threshold:
                position = Signal.LONG_A_SHORT_B
        else:
            if abs(current_z) < config.exit_threshold:
                position = Signal.FLAT

        signal.iloc[i] = position

    return pd.DataFrame({"spread": spread, "zscore": z, "signal": signal})
