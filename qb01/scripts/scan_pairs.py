from __future__ import annotations

import argparse
from dataclasses import dataclass

from quantbox.data.storage import load_candles
from quantbox.research.spread import build_spread, check_cointegration, half_life_mean_reversion
from quantbox.utils.logging import get_logger

log = get_logger(__name__)

DEFAULT_PAIRS: list[tuple[str, str]] = [
    ("SOLUSDT", "AVAXUSDT"),
    ("SOLUSDT", "ADAUSDT"),
    ("ATOMUSDT", "DOTUSDT"),
    ("POLUSDT", "ARBUSDT"),
    ("LTCUSDT", "BCHUSDT"),
]


@dataclass
class PairResult:
    symbol_a: str
    symbol_b: str
    data_points: int
    p_value: float | None
    half_life: float | None
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan cointegration across multiple pairs.")
    parser.add_argument("--interval", default="1h", help="Candle interval, default 1h")
    parser.add_argument("--exchange", default="binance", help="Exchange, default binance")
    parser.add_argument(
        "--zscore-window",
        type=int,
        default=30,
        help="Rolling window size for the zscore, in number of periods",
    )
    parser.add_argument(
        "--pairs",
        nargs="+",
        metavar="SYMBOL_A:SYMBOL_B",
        help="Custom list of pairs to test, for example SOLUSDT:AVAXUSDT. "
        "Defaults to a built in candidate list if omitted.",
    )
    return parser.parse_args()


def parse_pairs(raw_pairs: list[str] | None) -> list[tuple[str, str]]:
    if not raw_pairs:
        return DEFAULT_PAIRS

    parsed = []
    for entry in raw_pairs:
        if ":" not in entry:
            raise ValueError(f"Invalid pair format: {entry!r}, expected SYMBOL_A:SYMBOL_B")
        symbol_a, symbol_b = entry.split(":", 1)
        parsed.append((symbol_a.upper(), symbol_b.upper()))
    return parsed


def evaluate_pair(
    symbol_a: str,
    symbol_b: str,
    interval: str,
    exchange: str,
    zscore_window: int,
) -> PairResult:
    df_a = load_candles(symbol_a, interval=interval, exchange=exchange)
    df_b = load_candles(symbol_b, interval=interval, exchange=exchange)

    if df_a.empty or df_b.empty:
        return PairResult(
            symbol_a, symbol_b, data_points=0, p_value=None, half_life=None,
            error="missing data, run qb collect for both symbols",
        )

    aligned = df_a[["close"]].join(df_b[["close"]], how="inner", lsuffix="_a", rsuffix="_b")

    if len(aligned) < zscore_window * 2:
        return PairResult(
            symbol_a, symbol_b, data_points=len(aligned), p_value=None, half_life=None,
            error="not enough overlapping data points",
        )

    price_a = aligned["close_a"]
    price_b = aligned["close_b"]

    result = check_cointegration(price_a, price_b)
    spread = build_spread(price_a, price_b, ratio=result.hedge_ratio)
    half_life = half_life_mean_reversion(spread)

    return PairResult(
        symbol_a, symbol_b, data_points=len(aligned), p_value=result.p_value, half_life=half_life,
    )


def format_half_life(half_life: float | None) -> str:
    if half_life is None:
        return "n/a"
    if half_life == float("inf"):
        return "inf"
    return f"{half_life:.1f}"


def print_report(results: list[PairResult]) -> None:
    # Pairs with a valid p value first, sorted from most to least promising
    scored = [r for r in results if r.p_value is not None]
    failed = [r for r in results if r.p_value is None]
    scored.sort(key=lambda r: r.p_value if r.p_value is not None else float("inf"))

    header = f"{'Pair':<24}{'Points':>8}{'P value':>12}{'Half life':>12}{'Verdict':>16}"
    print()
    print(header)
    print("=" * len(header))

    for r in scored:
        assert r.p_value is not None  # guaranteed by the filter above
        verdict = "cointegrated" if r.p_value < 0.05 else "no evidence"
        pair_label = f"{r.symbol_a}/{r.symbol_b}"
        print(
            f"{pair_label:<24}{r.data_points:>8}"
            f"{r.p_value:>12.4f}{format_half_life(r.half_life):>12}{verdict:>16}"
        )

    for r in failed:
        pair_label = f"{r.symbol_a}/{r.symbol_b}"
        print(f"{pair_label:<24}skipped, {r.error or 'error'}")

    print()
    candidates = [r for r in scored if r.p_value is not None and r.p_value < 0.05]
    if candidates:
        print(f"{len(candidates)} pair(s) show evidence of cointegration at the 5 percent level.")
        print("These are candidates for deeper analysis, not validated strategies.")
    else:
        print("No pair in this scan showed evidence of cointegration at the 5 percent level.")

    print()
    print(
        "Reminder: cointegration alone does not validate a strategy. "
        "Out of sample backtesting is required before drawing any conclusion."
    )


def main() -> None:
    args = parse_args()
    pairs = parse_pairs(args.pairs)

    results = []
    for symbol_a, symbol_b in pairs:
        log.info("Evaluating %s / %s", symbol_a, symbol_b)
        results.append(
            evaluate_pair(symbol_a, symbol_b, args.interval, args.exchange, args.zscore_window)
        )

    print_report(results)


if __name__ == "__main__":
    main()