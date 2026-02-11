import asyncio
import logging
from datetime import datetime, timedelta

import yfinance as yf
from data_logger import cache_earnings, get_cached_earnings

logger = logging.getLogger(__name__)
CACHE_TTL_DAYS = 30


async def _fetch_earnings_from_yfinance(symbol):
    symbol = symbol.upper()

    def _fetch():
        ticker = yf.Ticker(symbol)
        try:
            # 抓取未来多个财报日，通常返回 4-8 个
            df = ticker.get_earnings_dates(limit=8)
        except Exception as exc:
            logger.error(f"yfinance earnings fetch failed for {symbol}: {exc}")
            return None

        if getattr(df, 'empty', False):
            return None

        # 提取所有未来的日期，存为逗号分隔字符串
        future_dates = []
        now = datetime.now()
        for dt in df.index:
            # 处理时区或转换
            if hasattr(dt, 'to_pydatetime'):
                dt_obj = dt.to_pydatetime().replace(tzinfo=None)
            else:
                dt_obj = dt.replace(tzinfo=None)
            
            if dt_obj >= now:
                future_dates.append(dt_obj.strftime('%Y-%m-%d'))
        
        return ",".join(sorted(list(set(future_dates)))) if future_dates else None

    return await asyncio.to_thread(_fetch)


async def is_near_earnings(symbol, within_days=3):
    symbol = symbol.upper()
    now = datetime.now()
    horizon = now + timedelta(days=within_days)
    
    # 1. 检查缓存
    try:
        cached = await get_cached_earnings(symbol, CACHE_TTL_DAYS)
        if cached:
            dates_str = cached.get('earnings_dates')
            if not dates_str:
                # 记录过没财报，且缓存没过期
                return False
            
            dates = dates_str.split(',')
            any_near = False
            has_future = False
            for d_str in dates:
                d_dt = datetime.strptime(d_str, '%Y-%m-%d')
                if d_dt >= now:
                    has_future = True
                    if now <= d_dt <= horizon:
                        logger.info(f"📅 缓存命中：{symbol} 近期财报 {d_str}")
                        any_near = True
                        break
            
            # 如果缓存里还有未来的日期，且没有一个是“近期”，则直接返回 False
            if has_future:
                return any_near
            # 如果缓存里所有日期都过时了，说明需要重新拉取
    except Exception as e:
        logger.warning(f"读取财报缓存失败: {symbol} - {e}")

    # 2. 缓存未命中、过期或所有日期都已过时，调用 API
    logger.info(f"🔍 正在同步 {symbol} 的年度财报日历...")
    dates_str = await _fetch_earnings_from_yfinance(symbol)
    
    # 3. 写入缓存
    try:
        await cache_earnings(symbol, dates_str)
    except Exception as e:
        logger.warning(f"写入财报缓存失败: {e}")

    if not dates_str:
        return False

    # 4. 判断
    for d_str in dates_str.split(','):
        d_dt = datetime.strptime(d_str, '%Y-%m-%d')
        if now <= d_dt <= horizon:
            logger.info(f"⚠️ [Yahoo] 检测到 {symbol} 近期财报：{d_str}")
            return True
            
    return False
