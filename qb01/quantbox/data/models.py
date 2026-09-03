"""Data models for market data. OHLCV candles only for now.

Using these models everywhere a candle flows through the system, from API response
to normalization to storage, ensures raw exchange formats never leak into the rest
of the codebase.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Candle(BaseModel):
    """A normalized OHLCV candle, independent of its source exchange."""

    exchange: str
    symbol: str
    interval: str
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: datetime

    def to_row(self) -> dict:
        """Representation ready for database insertion."""
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "interval": self.interval,
            "open_time": self.open_time,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "close_time": self.close_time,
        }


class CollectRequest(BaseModel):
    """Parameters for a historical data collection request."""

    symbol: str
    interval: str = "1h"
    days: int = Field(default=30, gt=0, le=1000)
