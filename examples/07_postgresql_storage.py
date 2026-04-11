"""
07 — PostgresStorage (on-premise enterprise backend).

Requires psycopg2. Install:
    pip install sentinel-kernel[postgres]

Requires a running PostgreSQL (or compatible) instance. For a local
throwaway database:

    docker run -d --name sentinel-pg \
        -e POSTGRES_PASSWORD=test -e POSTGRES_USER=sentinel \
        -e POSTGRES_DB=sentinel -p 5432:5432 postgres:15-alpine

    export SENTINEL_PG="postgresql://sentinel:test@localhost:5432/sentinel"

This example skips itself gracefully if psycopg2 is not installed
or if SENTINEL_PG is unset, so it is safe to run in CI without a
real database.

Run:
    python examples/07_postgresql_storage.py
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        print("psycopg2 not installed. Install: pip install sentinel-kernel[postgres]")
        print("Skipping.")
        return 0

    dsn = os.environ.get("SENTINEL_PG")
    if not dsn:
        print("SENTINEL_PG env var not set. Set it to a PostgreSQL DSN to run.")
        print("  export SENTINEL_PG='postgresql://user:pass@host:5432/db'")
        print("Skipping.")
        return 0

    from sentinel import Sentinel
    from sentinel.storage.postgres import PostgresStorage

    storage = PostgresStorage(dsn)
    sentinel = Sentinel(storage=storage, project="pg-demo")

    @sentinel.trace
    def record(value: int) -> dict:
        return {"value": value, "squared": value * value}

    for v in range(3):
        record(v)

    traces = sentinel.query(limit=10)
    print(f"Wrote {len(traces)} traces to PostgreSQL")
    for t in traces:
        print(f"  {t.trace_id[:12]}  {t.agent}  {t.started_at.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
