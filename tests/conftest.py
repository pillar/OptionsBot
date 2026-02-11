import asyncio
import sys
from pathlib import Path

# Ensure there's always an event loop when ib_insync/eventkit import runs.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Add repo root to sys.path so tests can import project modules even when under tests/ package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
