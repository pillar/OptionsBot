import asyncio
import sqlite3
from datetime import datetime, timedelta

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

EARNINGS_CACHE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS earnings_cache (
    symbol TEXT PRIMARY KEY,
    earnings_date TEXT,
    fetched_at TEXT NOT NULL
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
    conn.execute(EARNINGS_CACHE_TABLE_SQL)
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


def _get_cached_earnings_sync(symbol, max_age_hours):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT earnings_date, fetched_at FROM earnings_cache WHERE symbol = ?",
        (symbol.upper(),)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    fetched = datetime.fromisoformat(row[1])
    if datetime.utcnow() - fetched > timedelta(hours=max_age_hours):
        return None

    return {
        'earnings_date': row[0],
        'fetched_at': row[1]
    }


def _cache_earnings_sync(symbol, earnings_date):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO earnings_cache (symbol, earnings_date, fetched_at) VALUES (?, ?, ?) "
        "ON CONFLICT(symbol) DO UPDATE SET earnings_date=excluded.earnings_date, fetched_at=excluded.fetched_at",
        (
            symbol.upper(),
            earnings_date,
            datetime.utcnow().isoformat()
        )
    )
    conn.commit()
    conn.close()


async def ensure_db():
    await asyncio.to_thread(_init_db)


async def log_trade(trade_type, symbol, action, quantity=None, price=None, delta=None, notes=None):
    await asyncio.to_thread(_log_trade_sync, trade_type, symbol, action, quantity, price, delta, notes)


async def log_market_snapshot(symbol, value, notes=None):
    await asyncio.to_thread(_log_market_sync, symbol, value, notes)


async def get_cached_earnings(symbol, max_age_hours=6):
    return await asyncio.to_thread(_get_cached_earnings_sync, symbol, max_age_hours)


async def cache_earnings(symbol, earnings_date):
    await asyncio.to_thread(_cache_earnings_sync, symbol, earnings_date)
