import json
import sqlite3
from statistics import mean
from typing import Optional

from config import DB_PATH, LEARNED_CONFIG_PATH, load_parameters, save_learned_config


def _average_delta_for_type(cursor, trade_type):
    cursor.execute(
        "SELECT delta FROM trades WHERE trade_type = ? AND delta IS NOT NULL",
        (trade_type,)
    )
    rows = [row[0] for row in cursor.fetchall() if row[0] is not None]
    return mean(rows) if rows else None


def tune_parameters(mode: str = 'base') -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    covered_delta = _average_delta_for_type(cursor, 'COVERED_CALL')
    roll_delta = _average_delta_for_type(cursor, 'ROLLING')
    spread_delta = _average_delta_for_type(cursor, 'SPREAD')
    conn.close()

    tuned = {}
    base_params = load_parameters(mode)
    if covered_delta:
        tuned['CC_DELTA_TARGET'] = round(min(covered_delta, base_params['CC_DELTA_TARGET'] + 0.05), 3)
    if roll_delta:
        tuned['ROLL_DELTA_THRESHOLD'] = round(min(roll_delta + 0.05, 1.0), 3)
    if spread_delta:
        tuned['PCS_SELL_DELTA'] = round(spread_delta, 3)

    if tuned:
        save_learned_config(mode, tuned)
    return tuned


def summarize(mode: str = 'base') -> dict:
    try:
        with LEARNED_CONFIG_PATH.open() as f:
            tuned = json.load(f)
        return tuned.get(mode, {})
    except Exception:
        return {}


if __name__ == '__main__':
    params = tune_parameters()
    print("Tuned parameters:", json.dumps(params, indent=2))
    print("Current learned config:", summarize())
