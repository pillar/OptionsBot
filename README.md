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

## Configuring Targets
- Customize `target_list.py` to define your own favorite stock/index pools and minimum holding thresholds; the strategy will pick whichever candidate currently satisfies the criteria.

## Safety
- **Daily Drawdown**: 1% (Automatic Emergency Exit)
- **Net Credit**: All rolls must be profitable after costs.
- **Trading Hours**: Only runs during RTH (9:30-16:00 EST).

## Testing & Documentation
- **Unit tests**: `pytest tests/` (passes after ensuring `.venv` is activated). Current suite covers `options_lookup` helpers and `test_search` smoke flow.
- **Smoke test**: `pytest tests/test_search.py` (leverages the shared `options_lookup.find_contract_by_delta` + `is_contract_liquid`).
- **Release notes**: See `release-notes.md` for an episodic history of major changes.
