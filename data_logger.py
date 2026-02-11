import asyncio
import sqlite3
from datetime import datetime

from config import DB_PATH

TRADES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    trade_type TEXT NOT NULL,
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    quantity REAL,
    price REAL,
    delta REAL,
    notes TEXT
)
"""

MARKET_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    value REAL,
    notes TEXT
)
"""

INSERT_TRADE_SQL = """
INSERT INTO trades (timestamp, trade_type, symbol, action, quantity, price, delta, notes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

INSERT_MARKET_SQL = """
INSERT INTO market_snapshots (timestamp, symbol, value, notes)
VALUES (?, ?, ?, ?)
"""


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(TRADES_TABLE_SQL)
    conn.execute(MARKET_TABLE_SQL)
    conn.commit()
    conn.close()


def _log_trade_sync(trade_type, symbol, action, quantity, price, delta, notes):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(INSERT_TRADE_SQL, (
        datetime.utcnow().isoformat(),
        trade_type,
        symbol,
        action,
        quantity,
        price,
        delta,
        notes
    ))
    conn.commit()
    conn.close()


def _log_market_sync(symbol, value, notes):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(INSERT_MARKET_SQL, (
        datetime.utcnow().isoformat(),
        symbol,
        value,
        notes
    ))
    conn.commit()
    conn.close()


async def ensure_db():
    await asyncio.to_thread(_init_db)


async def log_trade(trade_type, symbol, action, quantity=None, price=None, delta=None, notes=None):
    await asyncio.to_thread(_log_trade_sync, trade_type, symbol, action, quantity, price, delta, notes)


async def log_market_snapshot(symbol, value, notes=None):
    await asyncio.to_thread(_log_market_sync, symbol, value, notes)
