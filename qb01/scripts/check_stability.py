"""Rolling window stability check for a cointegration result
A single cointegration test on one fixed period can be misleading. The relationship
might only have looked stable because of what happened during that specific window,
rather than because the two assets are genuinely linked over time.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import pandas as pd

from quantbox.data.storage import load_candles
from quantbox.research.spread import build_spread, check_cointegration, half_life_mean_reversion
from quantbox.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class WindowResult:
    window_start: pd.Timestamp
    window_end: pd.Timestamp
    p_value: float
    half_life: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether a cointegration result is stable across time windows."
    )
    parser.add_argument("symbol_a", help="First symbol, for example SOLUSDT")
    parser.add_argument("symbol_b", help="Second symbol, for example AVAXUSDT")
    parser.add_argument("--interval", default="1h", help="Candle interval, default 1h")
    parser.add_argument("--exchange", default="binance", help="Exchange, default binance")
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Length of each rolling window, in days. Default 30.",
    )
    parser.add_argument(
        "--step-days",
        type=int,
        default=10,
        help="How far to move forward between windows, in days. Default 10, which "
        "means windows overlap since they are longer than the step.",
    )
    return parser.parse_args()


def build_windows(
    index: pd.DatetimeIndex, window_days: int, step_days: int
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Build a list of overlapping (start, end) timestamps covering the full index.

    Windows overlap on purpose, since step_days is normally smaller than
    window_days. This gives more windows to evaluate than non overlapping
    slicing would, without needing more raw data.
    """
    if len(index) == 0:
        return []

    start = index[0]
    end = index[-1]
    window = pd.Timedelta(days=window_days)
    step = pd.Timedelta(days=step_days)

    windows = []
    current_start = start
    while current_start + window <= end:
        windows.append((current_start, current_start + window))
        current_start += step

    return windows


def evaluate_windows(
    price_a: pd.Series,
    price_b: pd.Series,
    window_days: int,
    step_days: int,
) -> list[WindowResult]:
    windows = build_windows(price_a.index, window_days, step_days)
    results = []

    for window_start, window_end in windows:
        segment_a = price_a.loc[window_start:window_end]
        segment_b = price_b.loc[window_start:window_end]

        # Skip a window if either segment is too thin to produce a meaningful test,
        # which can happen near data gaps
        if len(segment_a) < 20 or len(segment_b) < 20:
            continue

        result = check_cointegration(segment_a, segment_b)
        spread = build_spread(segment_a, segment_b, ratio=result.hedge_ratio)
        half_life = half_life_mean_reversion(spread)

        results.append(WindowResult(window_start, window_end, result.p_value, half_life))

    return results


def print_report(results: list[WindowResult], symbol_a: str, symbol_b: str) -> None:
    if not results:
        print("No window produced a valid result. Try a smaller --window-days value,")
        print("or collect more historical data first.")
        return

    print()
    print(f"Rolling cointegration check: {symbol_a} / {symbol_b}")
    print(f"Number of windows evaluated: {len(results)}")
    print()

    header = f"{'Window start':<20}{'Window end':<20}{'P value':>10}{'Half life':>12}"
    print(header)
    print("=" * len(header))

    significant_count = 0
    for r in results:
        is_significant = r.p_value < 0.05
        if is_significant:
            significant_count += 1
        flag = "*" if is_significant else " "
        half_life_str = "inf" if r.half_life == float("inf") else f"{r.half_life:.1f}"
        print(
            f"{r.window_start.strftime('%Y-%m-%d'):<20}"
            f"{r.window_end.strftime('%Y-%m-%d'):<20}"
            f"{r.p_value:>10.4f}{half_life_str:>12}{flag:>3}"
        )

    fraction = significant_count / len(results)
    print()
    print(f"Windows with p value below 0.05: {significant_count} out of {len(results)} "
          f"({fraction:.0%})")
    print()

    if fraction >= 0.7:
        print("The relationship holds across most windows. This is a reasonably")
        print("stable candidate, though backtesting is still required.")
    elif fraction >= 0.3:
        print("The relationship holds in some windows but not others. Treat the")
        print("full period result with caution, it may not be reliable going forward.")
    else:
        print("The relationship rarely holds outside of specific windows. The full")
        print("period result was likely dominated by a short lived coincidence.")


def main() -> None:
    args = parse_args()

    log.info("Loading %s and %s", args.symbol_a, args.symbol_b)
    df_a = load_candles(args.symbol_a, interval=args.interval, exchange=args.exchange)
    df_b = load_candles(args.symbol_b, interval=args.interval, exchange=args.exchange)

    if df_a.empty or df_b.empty:
        log.error("No data found for one of the two symbols. Run qb collect first.")
        sys.exit(1)

    aligned = df_a[["close"]].join(df_b[["close"]], how="inner", lsuffix="_a", rsuffix="_b")
    if aligned.empty:
        log.error("No overlapping data points between the two symbols.")
        sys.exit(1)

    results = evaluate_windows(
        aligned["close_a"], aligned["close_b"], args.window_days, args.step_days
    )
    print_report(results, args.symbol_a, args.symbol_b)


if __name__ == "__main__":
    main()