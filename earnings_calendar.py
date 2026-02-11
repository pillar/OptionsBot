import csv
from datetime import datetime, timedelta
from pathlib import Path

CALENDAR_PATH = Path(__file__).with_name('earnings_calendar.csv')


def load_calendar():
    if not CALENDAR_PATH.exists():
        return []
    events = []
    with CALENDAR_PATH.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt = datetime.strptime(f"{row['date']} {row.get('time', '00:00')}", '%Y-%m-%d %H:%M')
            except ValueError:
                continue
            events.append({
                'symbol': row['symbol'].strip().upper(),
                'datetime': dt
            })
    return events


def upcoming_events(symbol=None, within_days=3):
    now = datetime.now()
    horizon = now + timedelta(days=within_days)
    events = load_calendar()
    matches = [e for e in events if now <= e['datetime'] <= horizon]
    if symbol:
        symbol = symbol.upper()
        matches = [e for e in matches if e['symbol'] == symbol]
    return matches


def is_near_earnings(symbol, within_days=2):
    symbol = symbol.upper()
    events = upcoming_events(symbol, within_days)
    return len(events) > 0
