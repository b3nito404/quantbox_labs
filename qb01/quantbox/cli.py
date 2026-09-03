"""Command line interface for QB-01.

Once the package is installed, all commands are available through the single entry
point: qb <command> ...

This file intentionally contains only command wiring, following the roadmap for
Phase 0 (data collection) and Phase 2 (backtesting). Business logic lives in the
corresponding modules under quantbox.
"""

from __future__ import annotations

import click

from quantbox.utils.logging import get_logger

log = get_logger(__name__)


@click.group()
def main() -> None:
    """QB-01: Statistical Arbitrage Research Engine, QuantBox Labs."""


@main.command()
@click.option("--symbol", required=True, help="Symbol to collect, for example BTCUSDT")
@click.option("--interval", default="1h", show_default=True, help="Candle interval")
@click.option(
    "--days", default=30, show_default=True, type=int, help="Number of days of history"
)
def collect(symbol: str, interval: str, days: int) -> None:
    """Collect historical OHLCV data from Binance and store it in the database."""
    from quantbox.data.binance_client import fetch_klines_range
    from quantbox.data.storage import save_candles

    log.info("Collecting %s (%s, %d days)", symbol, interval, days)
    candles = fetch_klines_range(symbol, interval=interval, days=days)
    saved = save_candles(candles)
    log.info("Saved %d candles for %s", saved, symbol)


@main.command()
@click.argument("strategy_path")
def backtest(strategy_path: str) -> None:
    """Run a backtest for the given strategy, for example strategy/stat_arb.

    Not implemented yet. The backtest engine is planned for a later development
    phase, once the research pipeline (data collection and signal generation) is
    validated end to end.
    """
    raise NotImplementedError(
        f"The backtest engine is not implemented yet (requested for: {strategy_path})."
    )


if __name__ == "__main__":
    main()
