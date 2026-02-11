import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'strategy_data.db'
LEARNED_CONFIG_PATH = BASE_DIR / 'learned_config.json'

DEFAULTS = {
    'CC_DELTA_TARGET': 0.15,
    'PCS_SELL_DELTA': 0.07,
    'PCS_WIDTH': 30,
    'ROLL_DELTA_THRESHOLD': 0.45,
    'ROLL_DTE_THRESHOLD': 1,
    'MAX_DAILY_DRAWDOWN': 0.01,
}

STRATEGY_MODES = {
    'base': {},
    'aggressive': {
        'CC_DELTA_TARGET': 0.25,        # 提高 Delta 以收取更多 Premium
        'PCS_SELL_DELTA': 0.15,       # 提高卖出端 Delta
        'PCS_WIDTH': 50,              # 增加宽度以获取更多信用
        'ROLL_DELTA_THRESHOLD': 0.55,  # 允许更靠近价内再滚动
        'MAX_DAILY_DRAWDOWN': 0.02,    # 容忍更高的日内波动
    }
}

DEFAULT_MODE = 'base'


def _build_mode_params(mode):
    params = DEFAULTS.copy()
    overrides = STRATEGY_MODES.get(mode, STRATEGY_MODES[DEFAULT_MODE])
    params.update(overrides)
    params['STRATEGY_MODE'] = mode
    return params


def load_parameters(mode: str = None):
    mode = mode or os.environ.get('STRATEGY_MODE', DEFAULT_MODE)
    params = _build_mode_params(mode)
    if LEARNED_CONFIG_PATH.exists():
        try:
            with LEARNED_CONFIG_PATH.open() as f:
                learned = json.load(f)
            mode_updates = learned.get(mode, {})
            params.update({k: v for k, v in mode_updates.items() if k in params})
        except Exception:
            pass
    return params


def save_learned_config(mode: str, params: dict):
    LEARNED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if LEARNED_CONFIG_PATH.exists():
        try:
            with LEARNED_CONFIG_PATH.open('r') as f:
                data = json.load(f)
        except Exception:
            data = {}
    data.setdefault(mode, {}).update(params)
    with LEARNED_CONFIG_PATH.open('w') as f:
        json.dump(data, f, indent=2)
