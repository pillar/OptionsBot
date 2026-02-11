import asyncio

# Ensure there's always an event loop when ib_insync/eventkit import runs.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
