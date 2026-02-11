# OptionsBot - Professional AI Options Trader

## Overview
Automated weekly options trading system that selects candidates from a configurable stock/index pool:
1. **Covered Call**: rent collection with auto-rolling on held equities (default pool includes GOOG/AAPL/MSFT).
2. **Put Credit Spread**: builds low-delta spreads using the hierarchy in `target_list.py` (default includes SPX).

## Setup
1. **Requirements**: Python 3.11+
2. **Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **IBKR Setup**: Ensure TWS/Gateway is running with API enabled on port 7497.

## Usage
- Run strategy: `python main.py`
- Test search logic: `pytest tests/test_search.py`
- Run unit tests: `pytest tests/`

## Strategy Comparison
- **Covered Call lane (stock-based)**: you collect rent on held equities from `target_list.py` (default GOOG/AAPL/MSFT) by selling Delta≈0.15 calls and rolling when Delta>0.45 or DTE<1. The puts are protected by the fact you own the shares.
- **Put Credit Spread lane (index-based)**: sells low-Delta(short) index puts and buys a protective leg 20–50 points below. It generates income with capped risk and no need to own the underlying index.

These two lanes remain separate so each can be monitored, measured, and risk-managed on its own. If you ever decide to merge them into a delta-hedged combo, describe the target in `TODO.md`/`CLAUDE.md` so we can plan the integration.

## Configuration & Self-Strengthening
- **`config.py`**: Central hub for all adjustable parameters (Delta, Rolling thresholds, Drawdown limits).
- **`target_list.py`**: Define your favorite tickers and minimum share requirements.
- **VIX Environmental Awareness**: The bot monitors VIX; it automatically reduces risk (lower Delta) or pauses entries during market panic (>30-40 VIX).
- **Auto-Tuning (`self_tuner.py`)**: Every hour, the bot analyzes its execution history in SQLite and updates `learned_config.json` to optimize its mathematical targets based on real-world performance.
- **SQLite Data Logging**: The bot automatically saves every trade, roll, and emergency exit to `strategy_data.db`. This data forms the foundation for future self-optimization and feedback loops.

## Safety
- **Daily Drawdown**: 1% (Automatic Emergency Exit)
- **Net Credit**: All rolls must be profitable after costs.
- **Trading Hours**: Only runs during RTH (9:30-16:00 EST).

## Testing & Documentation
- **Unit tests**: `pytest tests/` (passes after ensuring `.venv` is activated). Current suite covers `options_lookup` helpers and `test_search` smoke flow.
- **Smoke test**: `pytest tests/test_search.py` (leverages the shared `options_lookup.find_contract_by_delta` + `is_contract_liquid`).
- **Release notes**: See `release-notes.md` for an episodic history of major changes.
