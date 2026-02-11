# OptionsBot: 可配置的标的列表

# 股票候选池：按优先级排序。
# 机器人会检查账户中是否有满足 min_shares 的持仓。
STOCK_CANDIDATES = [
    {"symbol": "GOOG", "min_shares": 100},
    {"symbol": "AAPL", "min_shares": 100},
    {"symbol": "MSFT", "min_shares": 100},
]

# 指数候选池：策略会从中选择标的进行 Spread 操作。
INDEX_CANDIDATES = [
    {"symbol": "SPX", "exchange": "CBOE"},
    {"symbol": "QQQ", "exchange": "NASDAQ"},
    {"symbol": "SPY", "exchange": "SMART"},
]
