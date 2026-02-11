import math
import logging
from datetime import datetime, time, timedelta
import pytz

logger = logging.getLogger(__name__)

def get_next_friday(offset_weeks=0):
    """获取下周五（或本周五）的日期字符串 YYYYMMDD"""
    now = datetime.now()
    # 0=Monday, 4=Friday
    days_ahead = 4 - now.weekday()
    if days_ahead <= 0: # 如果今天已经是周五或周末，取下周五
        days_ahead += 7
    target_date = now + timedelta(days=days_ahead + (offset_weeks * 7))
    return target_date.strftime('%Y%m%d')

def is_trading_hours():
    """检查是否处于美股常规交易时段 (9:30 AM - 4:00 PM EST)"""
    est = pytz.timezone('US/Eastern')
    now_est = datetime.now(est)
    
    # 周一到周五
    if now_est.weekday() >= 5:
        return False
        
    start_time = time(9, 30)
    end_time = time(16, 0)
    
    return start_time <= now_est.time() <= end_time

def validate_net_credit(new_credit, old_cost, contracts_count, commission_per_contract=1.5, slippage=0.02):
    """
    验证 Net Credit 是否覆盖成本
    New_Credit - Old_Cost > Commission + Slippage
    """
    total_commission = commission_per_contract * contracts_count * 2 # 开仓+平仓
    # slippage 通常按每手合约的点位计算，这里简化为固定数值或百分比
    min_profit_buffer = total_commission + (slippage * contracts_count * 100)
    
    net = (new_credit - old_cost) * 100 * contracts_count
    return net > min_profit_buffer, net
