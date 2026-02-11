import pytest
from unittest.mock import patch, MagicMock
from earnings_calendar import is_near_earnings
import config
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_is_near_earnings_with_cache_hit():
    # 模拟数据库缓存命中
    mock_cache = {
        "earnings_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
        "fetched_at": datetime.now().isoformat()
    }
    
    with patch("earnings_calendar.get_cached_earnings", return_value=mock_cache):
        # 即使没有 API Key，缓存命中也应返回 True
        assert await is_near_earnings("TSLA") is True

@pytest.mark.asyncio
async def test_is_near_earnings_api_fallback_and_cache():
    # 模拟缓存失效，API 返回成功
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "earningsCalendar": [{"symbol": "AAPL", "date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}]
    }
    
    with patch("earnings_calendar.get_cached_earnings", return_value=None):
        with patch("requests.get", return_value=mock_response):
            # 必须 patch config.load_parameters，因为 earnings_calendar 现在通过 config 模块调用它
            with patch("config.load_parameters", return_value={"FINNHUB_API_KEY": "fake_key"}):
                with patch("earnings_calendar.cache_earnings") as mock_cache_write:
                    result = await is_near_earnings("AAPL")
                    assert result is True
                    # 验证是否写入了缓存
                    mock_cache_write.assert_called_once()

@pytest.mark.asyncio
async def test_is_near_earnings_no_key_no_cache():
    # 强制让 cache_earnings 不抛出 sqlite 错误（模拟初始化成功）
    with patch("earnings_calendar.get_cached_earnings", return_value=None):
        with patch("config.load_parameters", return_value={"FINNHUB_API_KEY": ""}):
            with patch("earnings_calendar.cache_earnings"):
                assert await is_near_earnings("GOOG") is False
