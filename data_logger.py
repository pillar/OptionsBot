import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DB_PATH

CREATE_TABLE_SQL = """
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

INSERT_SQL = """
INSERT INTO trades (timestamp, trade_type, symbol, action, quantity, price, delta, notes)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


def _init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()


def _log_trade_sync(trade_type, symbol, action, quantity, price, delta, notes):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(INSERT_SQL, (
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


async def ensure_db():
    await asyncio.to_thread(_init_db)


async def log_trade(trade_type, symbol, action, quantity=None, price=None, delta=None, notes=None):
    await asyncio.to_thread(_log_trade_sync, trade_type, symbol, action, quantity, price, delta, notes)
