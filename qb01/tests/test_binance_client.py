"""Tests for quantbox.data.binance_client"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from quantbox.data.binance_client import MAX_LIMIT_PER_CALL, fetch_klines_range
from quantbox.data.models import Candle


def _make_candle(dt: datetime) -> Candle:
    return Candle(
        exchange="binance",
        symbol="TESTUSDT",
        interval="1h",
        open_time=dt,
        open=1.0,
        high=1.0,
        low=1.0,
        close=1.0,
        volume=1.0,
        close_time=dt + timedelta(hours=1),
    )


def test_fetch_klines_range_warns_on_large_shortfall(caplog):
    """A delisted or recently listed symbol returns far fewer candles than the
    requested period implies. This should be logged as a warning, not silently
    accepted, so the gap cannot be discovered only much later by comparing row
    counts across symbols
    """
    now = datetime.now(tz=UTC)
    short_history_start = now - timedelta(hours=253)
    short_batch = [_make_candle(short_history_start + timedelta(hours=i)) for i in range(253)]

    with patch("quantbox.data.binance_client.fetch_klines") as mock_fetch:
        mock_fetch.side_effect = [short_batch, []]
        result = fetch_klines_range("TESTUSDT", interval="1h", days=365)

    assert len(result) == 253
    assert any("far fewer" in record.message for record in caplog.records)


def test_fetch_klines_range_does_not_warn_on_full_history(caplog):
    """A symbol with a complete history should not trigger the shortfall warning,
    even though the very last batch is naturally smaller than a full page
    """
    now = datetime.now(tz=UTC)

    def fake_fetch(symbol, interval, start_time=None, end_time=None, limit=MAX_LIMIT_PER_CALL):
        if start_time >= now:
            return []
        hours = int((end_time - start_time).total_seconds() // 3600) + 1
        count = min(MAX_LIMIT_PER_CALL, hours)
        return [_make_candle(start_time + timedelta(hours=i)) for i in range(count)]

    with patch("quantbox.data.binance_client.fetch_klines", side_effect=fake_fetch):
        result = fetch_klines_range("TESTUSDT", interval="1h", days=30)

    assert len(result) >= 700 
    assert not any("far fewer" in record.message for record in caplog.records)