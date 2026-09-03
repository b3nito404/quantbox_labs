"""client for the Binance public API, market data only.

This client uses only public endpoints and requires no API key. It reads historical
market data exclusively and never places orders. Real execution will be a strictly
separate module, introduced only once a strategy has demonstrated a validated edge.

API reference: https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from quantbox.data.models import Candle
from quantbox.utils.logging import get_logger

log = get_logger(__name__)

BASE_URL = "https://api.binance.com"
KLINES_ENDPOINT = "/api/v3/klines"
MAX_LIMIT_PER_CALL = 1000  


class BinanceClientError(RuntimeError):
    """Raised when the Binance API returns an unexpected response."""


def _interval_to_timedelta(interval: str) -> timedelta:
    """Convert a Binance interval string, such as 1m, 1h or 1d, to a timedelta."""
    unit = interval[-1]
    value = int(interval[:-1])
    mapping = {
        "m": timedelta(minutes=value),
        "h": timedelta(hours=value),
        "d": timedelta(days=value),
        "w": timedelta(weeks=value),
    }
    if unit not in mapping:
        raise ValueError(f"Unsupported interval: {interval!r}")
    return mapping[unit]


def fetch_klines(
    symbol: str,
    interval: str = "1h",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = MAX_LIMIT_PER_CALL,
) -> list[Candle]:
    """Fetch a single batch of candles, at most 1000 candles per call.

    For a longer period, see fetch_klines_range, which paginates automatically.
    """
    params: dict[str, str | int] = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": min(limit, MAX_LIMIT_PER_CALL),
    }
    if start_time is not None:
        params["startTime"] = int(start_time.timestamp() * 1000)
    if end_time is not None:
        params["endTime"] = int(end_time.timestamp() * 1000)

    response = requests.get(f"{BASE_URL}{KLINES_ENDPOINT}", params=params, timeout=10)
    if response.status_code != 200:
        raise BinanceClientError(
            f"Binance returned {response.status_code} for {symbol}/{interval}: {response.text}"
        )

    raw = response.json()
    candles = []
    for entry in raw:
        candles.append(
            Candle(
                exchange="binance",
                symbol=symbol.upper(),
                interval=interval,
                open_time=datetime.fromtimestamp(entry[0] / 1000, tz=UTC),
                open=float(entry[1]),
                high=float(entry[2]),
                low=float(entry[3]),
                close=float(entry[4]),
                volume=float(entry[5]),
                close_time=datetime.fromtimestamp(entry[6] / 1000, tz=UTC),
            )
        )
    return candles


def fetch_klines_range(
    symbol: str,
    interval: str = "1h",
    days: int = 30,
) -> list[Candle]:
    """Fetch the full history over the given number of days, paginating automatically.

    Binance limits each call to 1000 candles. For a longer period, calls are repeated
    while advancing the time window each time.
    """
    end_time = datetime.now(tz=UTC)
    start_time = end_time - timedelta(days=days)
    step = _interval_to_timedelta(interval) * MAX_LIMIT_PER_CALL

    all_candles: list[Candle] = []
    window_start = start_time

    while window_start < end_time:
        window_end = min(window_start + step, end_time)
        log.info(
            "Fetching %s/%s from %s to %s",
            symbol,
            interval,
            window_start.isoformat(),
            window_end.isoformat(),
        )
        batch = fetch_klines(symbol, interval, start_time=window_start, end_time=window_end)
        if not batch:
            break
        all_candles.extend(batch)
        # Advance right after the last received candle to avoid duplicates or gaps
        window_start = batch[-1].close_time

    log.info("Total fetched for %s/%s: %d candles", symbol, interval, len(all_candles))
    return all_candles
