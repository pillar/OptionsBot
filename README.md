# OptionsBot - Professional AI Options Trader

## Overview
Automated weekly options trading system focusing on:
1. **GOOG Covered Call**: Rent collection with auto-rolling.
2. **SPX Put Credit Spread**: Low-delta probability income.

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
- Test search logic: `pytest test_search.py`
- Run unit tests: `pytest tests/`

## Safety
- **Daily Drawdown**: 1% (Automatic Emergency Exit)
- **Net Credit**: All rolls must be profitable after costs.
- **Trading Hours**: Only runs during RTH (9:30-16:00 EST).
