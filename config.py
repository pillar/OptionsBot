import json
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
    'FINNHUB_API_KEY': '', # 在此填写你的 Finnhub 免费 API Key 以开启自动财报过滤
}


def load_parameters():
    config = DEFAULTS.copy()
    if LEARNED_CONFIG_PATH.exists():
        try:
            with LEARNED_CONFIG_PATH.open('r') as f:
                learned = json.load(f)
            config.update({k: v for k, v in learned.items() if k in config})
        except Exception:
            pass
    return config


def save_learned_config(params: dict):
    LEARNED_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEARNED_CONFIG_PATH.open('w') as f:
        json.dump(params, f, indent=2)
