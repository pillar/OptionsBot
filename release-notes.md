# Release Notes

## 2026-02-11
- Initial commit of OptionsBot with main strategy, math helpers, documentation, and todo roadmap.
- Added `options_lookup` module, `is_contract_liquid` guard, unit tests, and smoke test using the shared lookup.
- Configured pytest + venv workflow, `.gitignore`, and released project to GitHub at `pillar/OptionsBot`.
- Latest test run: `pytest -v` (all 4 tests passed, warnings only around asyncio deprecation).
