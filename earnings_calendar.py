import asyncio
import logging
from datetime import datetime, timedelta

import yfinance as yf
from data_logger import cache_earnings, get_cached_earnings

logger = logging.getLogger(__name__)
CACHE_TTL_HOURS = 24


async def _fetch_earnings_from_yfinance(symbol):
    symbol = symbol.upper()

    def _fetch():
        ticker = yf.Ticker(symbol)
        try:
            df = ticker.get_earnings_dates(limit=1)
        except Exception as exc:
            logger.error(f"yfinance earnings fetch failed for {symbol}: {exc}")
            return None

        if getattr(df, 'empty', False):
            return None

        idx = df.index[0]
        if hasattr(idx, 'strftime'):
            return idx.strftime('%Y-%m-%d')
        return str(idx)

    return await asyncio.to_thread(_fetch)


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
                logger.info(f"📅 使用缓存：{symbol} 近期财报 {earnings_date}")
                return True
            return False
    except Exception:
        logger.warning(f"读取财报缓存失败: {symbol}")

    earnings_date = await _fetch_earnings_from_yfinance(symbol)
    try:
        await cache_earnings(symbol, earnings_date)
    except Exception:
        logger.warning("写入财报缓存失败")

    if not earnings_date:
        return False

    try:
        earnings_dt = datetime.strptime(earnings_date, '%Y-%m-%d')
        now = datetime.now()
        within = now <= earnings_dt <= now + timedelta(days=within_days)
        if within:
            logger.info(f"⚠️ [Yahoo] 检测到 {symbol} 近期财报：{earnings_date}")
        return within
    except ValueError:
        return False
