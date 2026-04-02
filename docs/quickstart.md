# Quickstart

## Prerequisites

- Python >= 3.11
- No other mandatory dependencies

---

## Install

From source (package not yet published to PyPI):

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel.git
cd sentinel-kernel
pip install -e .
```

---

## First trace

```python
import asyncio
from sentinel import Sentinel
from sentinel.storage import SQLiteStorage

sentinel = Sentinel(
    project="my-project",
    storage=SQLiteStorage(":memory:"),
)

@sentinel.trace
async def greet(name: str) -> dict:
    return {"message": f"Hello, {name}"}

async def main():
    await greet(name="Ada")
    traces = sentinel.query(project="my-project")
    print(traces[0].to_json())

asyncio.run(main())
```

Output (abbreviated):

```json
{
  "schema_version": "1.0.0",
  "trace_id": "...",
  "project": "my-project",
  "agent": "greet",
  "started_at": "2026-04-01T14:23:41.234000+00:00",
  "completed_at": "2026-04-01T14:23:41.236000+00:00",
  "latency_ms": 2,
  "inputs_hash": "...",
  "inputs": {"name": "Ada"},
  "output": {"message": "Hello, Ada"},
  "output_hash": "...",
  "model": {"provider": null, "name": null, "version": null, ...},
  "policy": null,
  "human_override": null,
  "sovereignty": {"data_residency": "local", "sovereign_scope": "local", "storage_backend": "sqlite"},
  "tags": {},
  "precedent_trace_ids": []
}
```

---

## Offline-first

Sentinel works with zero network access. No cloud account, no API key, no external service required. The SQLite and filesystem backends use only Python's standard library. This is intentional: the primary deployment target includes air-gapped and classified environments.

---

## Storage options

### SQLiteStorage (default, development)

```python
from sentinel.storage import SQLiteStorage

# In-memory (lost on process exit — useful for tests)
storage = SQLiteStorage(":memory:")

# Persistent file
storage = SQLiteStorage("/var/lib/sentinel/traces.db")
```

Good for: local development, single-node deployments, integration tests.

### FilesystemStorage (air-gapped, classified)

```python
from sentinel.storage import FilesystemStorage

storage = FilesystemStorage("/mnt/sovereign-storage/traces/")
```

Writes one NDJSON file per day. Append-only. No database process required. Designed for environments where SQLite is unavailable or undesirable.

Good for: air-gapped systems, write-once audit storage, log aggregation pipelines.

### Custom backend

Implement the `StorageBackend` abstract class:

```python
from sentinel.storage.base import StorageBackend

class MyStorage(StorageBackend):
    @property
    def backend_name(self) -> str:
        return "my-backend"

    def initialise(self) -> None: ...
    def save(self, trace) -> None: ...
    def query(self, project=None, agent=None, policy_result=None, limit=100, offset=0): ...
    def get(self, trace_id: str): ...
```

Pass your implementation to `Sentinel(storage=MyStorage())`.

---

## Inspecting traces

```python
# Query all traces for a project
traces = sentinel.query(project="my-project")

# Filter by agent
traces = sentinel.query(agent="approve_purchase_order")

# Filter by policy result
from sentinel import PolicyResult
traces = sentinel.query(policy_result=PolicyResult.DENY)

# Serialise a trace
trace = traces[0]
print(trace.to_dict())   # Python dict
print(trace.to_json())   # JSON string
```

---

## Adding a policy

Policies evaluate before the decorated function executes. Use `SimpleRuleEvaluator` for Python callables:

```python
from sentinel import Sentinel, PolicyDeniedError
from sentinel.storage import SQLiteStorage
from sentinel.policy import SimpleRuleEvaluator

def procurement_policy(inputs: dict) -> tuple[bool, str | None]:
    """Return (True, None) to ALLOW, (False, "reason") to DENY."""
    if inputs.get("amount_eur", 0) > 50_000:
        return False, "exceeds_threshold"
    return True, None

sentinel = Sentinel(
    project="procurement-agent",
    storage=SQLiteStorage(":memory:"),
    policy_evaluator=SimpleRuleEvaluator({
        "policies/procurement": procurement_policy,
    }),
)

@sentinel.trace(policy="policies/procurement")
async def approve(order_id: str, amount_eur: float) -> dict:
    return {"decision": "approved"}
```

---

## What a DENY looks like

When a policy returns DENY, Sentinel raises `PolicyDeniedError` before the decorated function runs. The trace is still written to storage with `policy.result = "DENY"` and the rule that triggered it.

```python
try:
    await approve(order_id="PO-2026-0099", amount_eur=120_000)
except PolicyDeniedError as e:
    print(e)  # includes trace ID and rule name

# The DENY trace is stored and queryable
denied = sentinel.query(policy_result=PolicyResult.DENY)
```

The function never executes. No side effects occur. The audit record is complete.

---

## Next steps

- [Schema reference](schema.md) — full field definitions and constraints
- [Architecture](architecture.md) — design principles and trace lifecycle
- [Integration guide](integration-guide.md) — wrapping existing agents and frameworks
- [Project status](project-status.md) — current maturity, known gaps, API stability
