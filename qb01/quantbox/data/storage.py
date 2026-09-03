"""Storage layer: writing and reading OHLCV candles in PostgreSQL.

This module uses SQLAlchemy Core rather than the full ORM. It is sufficient for this
volume of queries, simpler to reason about, and stays close to the raw SQL defined in
infra/docker/init.sql.
"""

from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from quantbox.data.models import Candle
from quantbox.utils.config import settings
from quantbox.utils.logging import get_logger

log = get_logger(__name__)

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return, and cache, the SQLAlchemy engine connected to PostgreSQL."""
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, future=True)
    return _engine


UPSERT_OHLCV_SQL = text(
    """
    INSERT INTO ohlcv (exchange, symbol, interval, open_time, open, high, low, close,
                        volume, close_time)
    VALUES (:exchange, :symbol, :interval, :open_time, :open, :high, :low, :close,
            :volume, :close_time)
    ON CONFLICT (exchange, symbol, interval, open_time) DO UPDATE
    SET open = EXCLUDED.open,
        high = EXCLUDED.high,
        low = EXCLUDED.low,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        close_time = EXCLUDED.close_time
    """
)


def save_candles(candles: list[Candle]) -> int:
    """Insert or update a list of candles. Returns the number of rows processed.

    The upsert, using ON CONFLICT DO UPDATE, makes this function idempotent. A
    collection can be run multiple times over the same period without creating
    duplicate rows.
    """
    if not candles:
        return 0

    engine = get_engine()
    rows = [c.to_row() for c in candles]
    with engine.begin() as conn:
        conn.execute(UPSERT_OHLCV_SQL, rows)

    log.info("Saved %d candles to the database", len(rows))
    return len(rows)


def load_candles(
    symbol: str,
    interval: str = "1h",
    exchange: str = "binance",
) -> pd.DataFrame:
    """Load all available candles for a given symbol, sorted chronologically.

    Returns a DataFrame indexed by open_time, ready for analysis in the research or
    backtest layers.
    """
    engine = get_engine()
    query = text(
        """
        SELECT open_time, open, high, low, close, volume
        FROM ohlcv
        WHERE exchange = :exchange AND symbol = :symbol AND interval = :interval
        ORDER BY open_time ASC
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(
            query,
            conn,
            params={"exchange": exchange, "symbol": symbol.upper(), "interval": interval},
            parse_dates=["open_time"],
        )

    return df.set_index("open_time")
