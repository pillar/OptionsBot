import requests
import logging
from datetime import datetime, timedelta
import config

logger = logging.getLogger(__name__)

def is_near_earnings(symbol, within_days=3):
    """
    通过 Finnhub API 实时检查标的是否在财报窗口内。
    """
    params = config.load_parameters()
    api_key = params.get('FINNHUB_API_KEY', '')
    
    if not api_key:
        return False

    try:
        now = datetime.now()
        start_date = now.strftime('%Y-%m-%d')
        end_date = (now + timedelta(days=within_days)).strftime('%Y-%m-%d')
        
        url = f"https://finnhub.io/api/v1/calendar/earnings?from={start_date}&to={end_date}&token={api_key}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return False
            
        data = response.json()
        earnings_calendar = data.get('earningsCalendar', [])
        
        symbol_upper = symbol.upper()
        for event in earnings_calendar:
            if event.get('symbol', '').upper() == symbol_upper:
                logger.info(f"⚠️ [API] 检测到 {symbol_upper} 近期财报：{event.get('date')}，跳过交易")
                return True
                
        return False
    except Exception as e:
        logger.error(f"Finnhub API 调用异常: {e}")
        return False
