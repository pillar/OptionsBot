import pytest
from unittest.mock import patch, MagicMock
from earnings_calendar import is_near_earnings
from datetime import datetime, timedelta
import pandas as pd

class DummyDF:
    def __init__(self, idx):
        self.index = idx

    @property
    def empty(self):
        return not self.index

@pytest.mark.asyncio
async def test_is_near_earnings_with_cache_hit():
    mock_cache = {
        "earnings_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
        "fetched_at": datetime.utcnow().isoformat()
    }
    with patch("earnings_calendar.get_cached_earnings", return_value=mock_cache):
        assert await is_near_earnings("TSLA") is True

@pytest.mark.asyncio
async def test_is_near_earnings_api_fallback_and_cache(monkeypatch):
    mock_date = pd.Timestamp(datetime.now() + timedelta(days=1))
    df = DummyDF([mock_date])

    def fake_cache_earnings(symbol, earnings_date):
        assert earnings_date == mock_date.strftime('%Y-%m-%d')

    class DummyTicker:
        def get_earnings_dates(self, limit=1):
            return df

    monkeypatch.setattr("earnings_calendar.yf.Ticker", lambda symbol: DummyTicker())
    monkeypatch.setattr("earnings_calendar.get_cached_earnings", lambda symbol, ttl: None)
    monkeypatch.setattr("earnings_calendar.cache_earnings", fake_cache_earnings)

    assert await is_near_earnings("AAPL") is True

@pytest.mark.asyncio
async def test_is_near_earnings_no_cache_and_empty():
    class DummyTicker:
        def get_earnings_dates(self, limit=1):
            return DummyDF([])

    with patch("earnings_calendar.yf.Ticker", lambda symbol: DummyTicker()):
        with patch("earnings_calendar.get_cached_earnings", return_value=None):
            with patch("earnings_calendar.cache_earnings"):
                assert await is_near_earnings("GOOG") is False
