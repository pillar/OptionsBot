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
    # 模拟数据库缓存命中，包含多个日期
    d1 = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    d2 = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')
    mock_cache = {
        "earnings_dates": f"{d1},{d2}",
        "fetched_at": datetime.now().isoformat()
    }
    with patch("earnings_calendar.get_cached_earnings", return_value=mock_cache):
        assert await is_near_earnings("TSLA") is True

@pytest.mark.asyncio
async def test_is_near_earnings_api_fallback_and_cache(monkeypatch):
    # 模拟缓存失效，API 返回两个日期
    t1 = pd.Timestamp(datetime.now() + timedelta(days=2))
    t2 = pd.Timestamp(datetime.now() + timedelta(days=92))
    df = DummyDF([t1, t2])

    def fake_cache_earnings(symbol, dates_str):
        expected = f"{t1.strftime('%Y-%m-%d')},{t2.strftime('%Y-%m-%d')}"
        assert dates_str == expected

    class DummyTicker:
        def get_earnings_dates(self, limit=8):
            return df

    monkeypatch.setattr("earnings_calendar.yf.Ticker", lambda symbol: DummyTicker())
    monkeypatch.setattr("earnings_calendar.get_cached_earnings", lambda symbol, ttl: None)
    monkeypatch.setattr("earnings_calendar.cache_earnings", fake_cache_earnings)

    assert await is_near_earnings("AAPL") is True

@pytest.mark.asyncio
async def test_is_near_earnings_no_cache_and_empty():
    class DummyTicker:
        def get_earnings_dates(self, limit=8):
            return DummyDF([])

    with patch("earnings_calendar.yf.Ticker", lambda symbol: DummyTicker()):
        with patch("earnings_calendar.get_cached_earnings", return_value=None):
            with patch("earnings_calendar.cache_earnings"):
                assert await is_near_earnings("GOOG") is False
