# Quickstart

## Prerequisites

- Python >= 3.11
- No other mandatory dependencies

---

## Install

From PyPI (once published):

```bash
pip install sentinel-kernel
```

From source:

```bash
git clone https://github.com/sentinel-kernel/sentinel-kernel.git
cd sentinel-kernel
pip install -e .
```

---

## First trace

```python
from sentinel import Sentinel
from sentinel.storage import SQLiteStorage

sentinel = Sentinel(
    project="my-project",
    storage=SQLiteStorage(":memory:"),
)

@sentinel.trace(agent="greet")
def greet(name: str) -> dict:
    return {"message": f"Hello, {name}"}

greet("Ada")

traces = sentinel.query()
for trace in traces:
    print(trace.to_json())
```

Output (formatted for readability):

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
  "policy": {"result": "NOT_EVALUATED", ...},
  "sovereignty": {"data_residency": "local", "storage_backend": "sqlite"},
  ...
}
```

---

## Offline-first

Sentinel works with zero network access. No cloud account, no API key, no external service required. The SQLite and filesystem backends are implemented using Python's standard library only. This is intentional: the primary deployment target includes air-gapped and classified environments.

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

Implement the `StorageBackend` abstract interface to plug in any storage layer — PostgreSQL, S3-compatible object storage, an existing audit log system, or anything else:

```python
from sentinel.storage import StorageBackend
from sentinel.models import DecisionTrace

class MyStorage(StorageBackend):
    def write(self, trace: DecisionTrace) -> None:
        ...

    def query(self, **filters) -> list[DecisionTrace]:
        ...
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
from sentinel.models import PolicyResult
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
from sentinel import Sentinel
from sentinel.storage import SQLiteStorage
from sentinel.policy import SimpleRuleEvaluator

def procurement_policy(inputs: dict) -> bool:
    """Return True to ALLOW, False to DENY."""
    return inputs.get("amount_eur", 0) <= 50_000

sentinel = Sentinel(
    project="procurement-agent",
    storage=SQLiteStorage(":memory:"),
    policy=SimpleRuleEvaluator(
        policy_id="policies/procurement.py",
        rule=procurement_policy,
    ),
)

@sentinel.trace(agent="approve_purchase_order")
def approve(order_id: str, amount_eur: float) -> dict:
    return {"decision": "approved"}

approve(order_id="PO-2026-0042", amount_eur=48_500)   # ALLOW
approve(order_id="PO-2026-0099", amount_eur=120_000)  # DENY — raises PolicyDeniedError
```

---

## What a DENY looks like

When a policy returns DENY, Sentinel raises `PolicyDeniedError` before the decorated function runs. The trace is still written to storage with `policy.result = "DENY"` and the rule that triggered it.

```python
from sentinel.exceptions import PolicyDeniedError

try:
    approve(order_id="PO-2026-0099", amount_eur=120_000)
except PolicyDeniedError as e:
    print(e)  # Policy DENY: policies/procurement.py

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
