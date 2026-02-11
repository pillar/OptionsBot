from pathlib import Path

# Adjustable strategy parameters (edit these to tune the behavior)
CC_DELTA_TARGET = 0.15
PCS_SELL_DELTA = 0.07
PCS_WIDTH = 30  # Strike spread width in dollars
ROLL_DELTA_THRESHOLD = 0.45
ROLL_DTE_THRESHOLD = 1
MAX_DAILY_DRAWDOWN = 0.01  # 1% daily drawdown limit

# Database path for logging executions
DB_PATH = Path(__file__).resolve().parent / 'strategy_data.db'
