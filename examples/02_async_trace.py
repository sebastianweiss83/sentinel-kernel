"""
02 — Async sovereign trace.

The @sentinel.trace decorator works transparently on async functions.
Same API, zero code changes compared to the sync version.

Run:
    python examples/02_async_trace.py
"""

import asyncio

from sentinel import Sentinel
from sentinel.storage import SQLiteStorage


async def main() -> None:
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="async-demo")

    @sentinel.trace
    async def fetch_and_decide(payload: dict) -> dict:
        # pretend there's an async I/O call here
        await asyncio.sleep(0.001)
        return {"decision": "approved", "request_id": payload.get("request_id")}

    await fetch_and_decide({"request_id": "req-001"})
    await fetch_and_decide({"request_id": "req-002"})

    for trace in sentinel.query(limit=5):
        print(f"{trace.started_at.isoformat()}  {trace.agent}  "
              f"latency={trace.latency_ms}ms")


if __name__ == "__main__":
    asyncio.run(main())
