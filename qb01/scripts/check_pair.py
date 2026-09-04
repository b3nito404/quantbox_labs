"""Cointegration analysis between two assets."""

from __future__ import annotations

import argparse
import sys

from quantbox.data.storage import load_candles
from quantbox.research.spread import (
    build_spread,
    check_cointegration,
    half_life_mean_reversion,
    zscore,
)
from quantbox.utils.logging import get_logger

log = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test cointegration between two symbols.")
    parser.add_argument("symbol_a", help="First symbol, for example BTCUSDT")
    parser.add_argument("symbol_b", help="Second symbol, for example ETHUSDT")
    parser.add_argument("--interval", default="1h", help="Candle interval, default 1h")
    parser.add_argument("--exchange", default="binance", help="Exchange, default binance")
    parser.add_argument(
        "--zscore-window",
        type=int,
        default=30,
        help="Rolling window size for the zscore, in number of periods",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    log.info("Loading %s from the database", args.symbol_a)
    df_a = load_candles(args.symbol_a, interval=args.interval, exchange=args.exchange)
    log.info("Loading %s from the database", args.symbol_b)
    df_b = load_candles(args.symbol_b, interval=args.interval, exchange=args.exchange)

    if df_a.empty or df_b.empty:
        log.error(
            "No data found for one of the two symbols. Run qb collect first for both."
        )
        sys.exit(1)

    
    aligned = df_a[["close"]].join(
        df_b[["close"]], how="inner", lsuffix="_a", rsuffix="_b"
    )

    if len(aligned) < args.zscore_window * 2:
        log.error(
            "Not enough overlapping data points (%d) to run a meaningful analysis.",
            len(aligned),
        )
        sys.exit(1)

    price_a = aligned["close_a"]
    price_b = aligned["close_b"]

    result = check_cointegration(price_a, price_b)
    spread = build_spread(price_a, price_b, ratio=result.hedge_ratio)
    z = zscore(spread, window=args.zscore_window)
    half_life = half_life_mean_reversion(spread)

    print()
    print(f"Pair: {args.symbol_a} / {args.symbol_b} ({args.interval}, {args.exchange})")
    print(f"Overlapping data points: {len(aligned)}")
    print(f"Period: {aligned.index[0]} to {aligned.index[-1]}")
    print()
    print(f"Hedge ratio: {result.hedge_ratio:.4f}")
    print(f"Cointegration p value: {result.p_value:.4f}")
    print(f"Cointegration test statistic: {result.test_statistic:.4f}")
    print(f"Half life of mean reversion: {half_life:.1f} periods")
    print()
    print(f"Current spread: {spread.iloc[-1]:.4f}")
    print(f"Current zscore: {z.iloc[-1]:.4f}")
    print()

    if result.p_value < 0.05:
        print("Result: the pair appears cointegrated at the 5 percent level.")
    else:
        print("Result: no strong evidence of cointegration at the 5 percent level.")

    if half_life != float("inf") and 0 < half_life < len(aligned) / 3:
        print("The estimated half life is within a plausible and exploitable range.")
    else:
        print("The estimated half life is too long, negative, or infinite to be useful.")

    print()
    print(
        "Reminder: these results alone do not validate a strategy. "
        "Out of sample backtesting is required before drawing any conclusion."
    )


if __name__ == "__main__":
    main()