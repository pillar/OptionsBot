import pytest
import csv
from datetime import datetime, timedelta
from pathlib import Path
from earnings_calendar import is_near_earnings, upcoming_events

def test_earnings_check(tmp_path):
    csv_file = tmp_path / "earnings.csv"
    now = datetime.now()
    future_date = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    far_date = (now + timedelta(days=10)).strftime('%Y-%m-%d')
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "date", "time"])
        writer.writerow(["TSLA", future_date, "16:00"])
        writer.writerow(["META", far_date, "16:00"])

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("earnings_calendar.CALENDAR_PATH", csv_file)
        
        # Near earnings
        assert is_near_earnings("TSLA", within_days=2) is True
        # Far from earnings
        assert is_near_earnings("META", within_days=2) is False
        # Not in list
        assert is_near_earnings("BABA", within_days=2) is False

def test_upcoming_events_logic(tmp_path):
    csv_file = tmp_path / "earnings.csv"
    now = datetime.now()
    date_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "date", "time"])
        writer.writerow(["GOOG", date_str, "16:00"])

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("earnings_calendar.CALENDAR_PATH", csv_file)
        events = upcoming_events(within_days=3)
        assert len(events) == 1
        assert events[0]['symbol'] == "GOOG"
