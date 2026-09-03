# QB-01: Statistical Arbitrage Research Engine

QB-01 is QuantBox Labs' first research system. It implements a complete pipeline
covering market data collection, storage, statistical research, signal generation,
and backtesting for statistical arbitrage strategies.

## Pipeline overview

Market data is collected from exchange public APIs and stored in PostgreSQL. The
research layer builds spreads between correlated instruments and evaluates their
statistical properties, such as cointegration and mean reversion. Strategies consume
these statistical signals to generate target positions. The backtest engine, still
under development, will simulate execution against historical data to evaluate net
performance after fees and slippage.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Running tests

```bash
pytest
```

## Code quality

```bash
ruff check .
mypy quantbox
```

## Command line interface

Once installed, the package exposes a `qb` command.

```bash
qb collect --symbol BTCUSDT --interval 1h --days 30
```
