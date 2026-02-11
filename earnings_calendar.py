import asyncio
import logging
from datetime import datetime, timedelta

import requests
import config
from data_logger import cache_earnings, get_cached_earnings

logger = logging.getLogger(__name__)
CACHE_TTL_HOURS = 24


async def _fetch_earnings_from_api(symbol, within_days):
    params = config.load_parameters()
    api_key = params.get('FINNHUB_API_KEY', '')
    if not api_key:
        return None

    now = datetime.now()
    start_date = now.strftime('%Y-%m-%d')
    end_date = (now + timedelta(days=max(within_days, 30))).strftime('%Y-%m-%d')
    
    url = (
        f"https://finnhub.io/api/v1/calendar/earnings"
        f"?from={start_date}&to={end_date}&token={api_key}"
    )
    try:
        response = await asyncio.to_thread(requests.get, url, timeout=10)
        if response.status_code != 200:
            return None
        data = response.json()
        events = data.get('earningsCalendar', [])
        
        for event in events:
            ev_symbol = event.get('symbol', '').upper()
            if ev_symbol == symbol.upper():
                return event.get('date')
        
        return None
    except Exception as exc:
        logger.error(f"Finnhub API 调用异常: {exc}")
        return None


async def is_near_earnings(symbol, within_days=3):
    symbol = symbol.upper()
    try:
        cached = await get_cached_earnings(symbol, CACHE_TTL_HOURS)
        if cached:
            earnings_date = cached.get('earnings_date')
            if not earnings_date:
                return False
            earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d')
            now = datetime.now()
            if now <= earnings_dt <= now + timedelta(days=within_days):
                return True
            return False
    except Exception:
        pass

    earnings_date = await _fetch_earnings_from_api(symbol, within_days)
    try:
        await cache_earnings(symbol, earnings_date)
    except Exception:
        pass

    if not earnings_date:
        return False

    try:
        earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d')
        now = datetime.now()
        within = now <= earnings_dt <= now + timedelta(days=within_days)
        return within
    except ValueError:
        return False
