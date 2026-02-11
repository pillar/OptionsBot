# Release Notes

## 2026-02-11
- Initial commit of OptionsBot with main strategy, math helpers, documentation, and todo roadmap.
- Added `options_lookup` module, `is_contract_liquid` guard, unit tests, and smoke test using the shared lookup.
- Configured pytest + venv workflow, `.gitignore`, and released project to GitHub at `pillar/OptionsBot`.
- Latest test run: `pytest -v` (all 4 tests passed, warnings only around asyncio deprecation).

## 2026-02-11 (later)
- Introduced `target_list.py` to hold configurable stock/index pools so the bot can rotate through whichever tickers you currently hold.
- `main.py` now selects candidates from the pool, applies the shared `options_lookup` logic, and runs index spreads/covered calls for those dynamically instead of hardcoding GOOG/SPX.
- Already documented the new config layer across README/AGENTS/TODO and pushed everything to GitHub.

## 2026-02-11 (docs)
- Updated README and CLAUDE instructions describing the configurable `target_list.py` with multi-ticker selection and the revised strategy flow.

## 2026-02-11 (smart earnings caching)
- Implemented intelligent multi-date earnings caching: fetches ~2 years of earnings dates via yfinance and stores them in SQLite.
- Smart refresh logic: only re-fetches when all cached dates have passed or after 30 days TTL, reducing API calls to "a few times per year".
- Removed Finnhub dependency; no API key required for earnings filtering.

## 2026-02-11 (self-learning & VIX)
- Integrated `vix_monitor.py` to track market fear levels; bot now adjusts Delta targets or pauses entries during high-volatility/panic phases.
- Implemented `self_tuner.py` which automatically analyzes SQLite trade history every hour to update `learned_config.json`, allowing the bot to "learn" from its own execution performance.
- Upgraded `main.py` to be environment-aware and fully configuration-driven.

