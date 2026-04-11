"""
01 — Minimal sovereign trace.

Fifteen lines. No config. No network. No cloud account.

Run:
    python examples/01_minimal_trace.py
"""

from sentinel import Sentinel
from sentinel.storage import SQLiteStorage


def main() -> None:
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="minimal")

    @sentinel.trace
    def decide(amount: int) -> dict:
        return {"decision": "approved", "amount": amount}

    decide(5_000)
    trace = sentinel.query(limit=1)[0]
    print(trace.to_json())


if __name__ == "__main__":
    main()
