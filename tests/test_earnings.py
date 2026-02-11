import pytest
from unittest.mock import patch, MagicMock
from earnings_calendar import is_near_earnings
import config

def test_is_near_earnings_with_api_hit():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "earningsCalendar": [
            {"symbol": "TSLA", "date": "2026-02-15"},
            {"symbol": "AAPL", "date": "2026-02-16"}
        ]
    }
    
    with patch("requests.get", return_value=mock_response):
        with patch.object(config, "load_parameters", return_value={"FINNHUB_API_KEY": "fake_key"}):
            assert is_near_earnings("TSLA") is True
            assert is_near_earnings("GOOG") is False

def test_is_near_earnings_no_api_key():
    with patch.object(config, "load_parameters", return_value={"FINNHUB_API_KEY": ""}):
        assert is_near_earnings("TSLA") is False

def test_is_near_earnings_api_error():
    mock_response = MagicMock()
    mock_response.status_code = 500
    
    with patch("requests.get", return_value=mock_response):
        with patch.object(config, "load_parameters", return_value={"FINNHUB_API_KEY": "fake_key"}):
            assert is_near_earnings("TSLA") is False
