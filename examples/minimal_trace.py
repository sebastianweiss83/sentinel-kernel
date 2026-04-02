"""
examples/minimal_trace.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Minimal example: trace a function and query the result.

Run: python examples/minimal_trace.py
"""

import asyncio

from sentinel import DataResidency, Sentinel
from sentinel.storage import SQLiteStorage

sentinel = Sentinel(
    storage=SQLiteStorage(":memory:"),
    project="minimal-example",
    data_residency=DataResidency.LOCAL,
)


@sentinel.trace
async def score_lead(company: str, employees: int) -> dict:
    score = min(100, employees // 10)
    return {"company": company, "score": score, "tier": "enterprise" if score > 50 else "smb"}


async def main():
    await score_lead(company="Acme GmbH", employees=800)

    traces = sentinel.query(project="minimal-example", limit=10)
    trace = traces[0]
    print(trace.to_json())


if __name__ == "__main__":
    asyncio.run(main())
