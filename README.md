# sentinel-kernel

**The EU-sovereign decision record layer for AI agents.**

Sentinel wraps agent execution, evaluates policy rules in-process, and writes append-only decision traces to local storage. It runs fully offline, has zero hard dependencies, and does not communicate with any external service. You own your data.

> **Status: Alpha.** Core trace schema and storage interfaces are stabilising. Not yet production-ready. API may change.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%2012%20Logging-003399)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)
[![Schema](https://img.shields.io/badge/Schema-v1.0.0--draft-orange)](docs/schema.md)
[![Governance](https://img.shields.io/badge/Governance-LF%20Europe%20intended-lightgrey)](https://linuxfoundation.eu)

---

## What Sentinel is

- Wraps agent function calls with a thin decorator — sync and async — without modifying agent logic
- Evaluates policy rules in-process before execution, producing a structured `PolicyResult` per call
- Records structured, SHA-256-hashed decision traces capturing inputs, outputs, policy evaluation, latency, and data residency metadata
- Works fully offline and in air-gapped environments — no network calls, no external dependencies
- Ships with pluggable storage: SQLite for structured querying, filesystem NDJSON for append-only log pipelines, or a custom backend via the `StorageBackend` interface
- Has no dependency on any cloud provider, model vendor, or hosted control plane

---

## What Sentinel is not

- Not an LLM gateway or proxy — it does not sit between your application and a model API
- Not a content moderation layer — it does not inspect or filter model outputs
- Not a hosted control plane — there is no Sentinel-managed cloud, dashboard, or SaaS offering
- Not tied to a model vendor — works with any model, any inference provider, or no model at all
- Not a SIEM or observability replacement — it produces decision records, not metrics, traces, or log aggregation

---

## Why it exists

The EU AI Act (Regulation 2024/1689) requires operators of high-risk AI systems to maintain logs of automated decisions, with records sufficient to reconstruct what happened and why. Article 12 obligations apply from 2 August 2026. Most existing logging approaches — cloud-hosted observability platforms, LLM gateway logs, third-party audit services — place decision records under foreign jurisdiction or create dependencies that conflict with data sovereignty requirements.

The US CLOUD Act means US-headquartered providers can be compelled to disclose data stored anywhere in the world. For AI systems deployed in regulated EU sectors — financial services, healthcare, critical infrastructure, public administration — this creates jurisdictional risk that cannot be mitigated by contractual means alone.

Sentinel is designed for deployments where the record of what an AI agent decided must remain within a controlled, auditable boundary. It is built for teams who need to demonstrate compliance without depending on a third-party platform to hold that evidence.

---

## Quick start

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel.git
cd sentinel-kernel
pip install -e .
```

```python
from sentinel import Sentinel
from sentinel.storage import SQLiteStorage

sentinel = Sentinel(
    storage=SQLiteStorage(":memory:"),
    project="demo",
)

@sentinel.trace
async def approve_discount(deal_id: str, amount: float) -> dict:
    return {"decision": "approve", "amount": amount}

# Every call produces a structured decision trace
result = await approve_discount("deal-42", amount=5000.0)

# Query traces
traces = sentinel.query(project="demo", limit=5)
print(traces[0].to_json())
```

Example trace output:

```json
{
  "schema_version": "1.0.0",
  "trace_id": "3f2a1b4c-8e7d-4f6a-9c2b-1d0e5f3a8b7c",
  "parent_trace_id": null,
  "project": "demo",
  "agent": "approve_discount",
  "started_at": "2026-04-02T09:14:32.104Z",
  "completed_at": "2026-04-02T09:14:32.107Z",
  "latency_ms": 3,
  "inputs_hash": "a4c2e1f8b3d790ef12c4a5b6d7e8f901...",
  "inputs": {
    "deal_id": "deal-42",
    "amount": 5000.0
  },
  "output": {
    "decision": "approve",
    "amount": 5000.0
  },
  "output_hash": "f7b1d3c9a2e4561b8c0d3e2f1a4b5c6d...",
  "model": {
    "provider": null,
    "name": null,
    "version": null,
    "tokens_input": null,
    "tokens_output": null
  },
  "policy": null,
  "human_override": null,
  "sovereignty": {
    "data_residency": "local",
    "sovereign_scope": "local",
    "storage_backend": "sqlite"
  },
  "tags": {},
  "precedent_trace_ids": []
}
```

---

## Architecture

```
Your agent function
        |
        v
+-------------------+
|  @sentinel.trace  |  <- Interceptor: captures inputs, timing, context
+--------+----------+
         |
         v
+-------------------+
|  Policy evaluator |  <- In-process: NullPolicy / SimpleRule / LocalRego (OPA)
+--------+----------+
         |
         v
+-------------------+
|  DecisionTrace    |  <- Serialized, hashed, sovereignty metadata attached
+--------+----------+
         |
         v
+-------------------+
|  StorageBackend   |  <- SQLite / Filesystem NDJSON / custom implementation
+-------------------+
```

**Interceptor** — The `@sentinel.trace` decorator wraps any sync or async function. It captures inputs, records start and end timestamps, computes SHA-256 hashes of inputs and outputs, and passes execution context to the policy evaluator before calling the underlying function.

**Policy evaluation** — Runs in-process before the agent function executes. Three evaluators ship with the package: `NullPolicyEvaluator` (default, always returns `NOT_EVALUATED`), `SimpleRuleEvaluator` (accepts Python callables), and `LocalRegoEvaluator` (shells out to a local OPA binary — no network call). Results are one of `ALLOW`, `DENY`, `EXCEPTION`, or `NOT_EVALUATED`.

**Trace serialization** — `DecisionTrace` is a dataclass with `to_dict()`, `to_json()`, and `from_dict()`. The schema includes sovereignty metadata (`DataResidency`, `sovereign_scope`, `storage_backend`) and supports human override records (`HumanOverride`).

**Storage backend** — `StorageBackend` is an abstract interface. `SQLiteStorage` provides full CRUD with indexing. `FilesystemStorage` appends NDJSON with daily log rotation. Custom backends implement the interface.

**Optional extras** — LangChain integration, PostgreSQL storage, and OpenTelemetry export are planned as optional extras and will not add to the zero-dependency core. See [docs/landscape.md](docs/landscape.md) for how Sentinel relates to the broader LLMOps and agent ecosystem.

---

## Current status

| Component | Status |
|---|---|
| `@sentinel.trace` decorator | Implemented — sync and async |
| `DecisionTrace` schema | Implemented — v1.0.0 draft |
| SQLite storage | Implemented |
| Filesystem / NDJSON storage | Implemented |
| `StorageBackend` interface | Implemented |
| `SimpleRuleEvaluator` | Implemented |
| `LocalRegoEvaluator` (OPA) | Implemented — requires OPA binary |
| Human override model | Implemented |
| LangChain integration | Planned (v0.3) |
| PostgreSQL storage | Planned |
| CLI (`sentinel` command) | Declared, not yet implemented |
| Test suite | 71 tests, 86% coverage |
| BSI IT-Grundschutz assessment | Planned (v1.0) |

---

## Repository structure

```
sentinel-kernel/
├── sentinel/
│   ├── __init__.py         # Public API: Sentinel, DecisionTrace, enums
│   ├── core/
│   │   ├── trace.py        # DecisionTrace, PolicyEvaluation, HumanOverride
│   │   └── tracer.py       # Sentinel class, @trace decorator, span(), query()
│   ├── policy/
│   │   └── evaluator.py    # NullPolicy, SimpleRule, LocalRego evaluators
│   └── storage/
│       ├── base.py         # StorageBackend abstract interface
│       ├── sqlite.py       # SQLiteStorage
│       └── filesystem.py   # FilesystemStorage (NDJSON)
├── docs/                   # Schema, architecture, compliance, quickstart
├── examples/               # Runnable examples
├── tests/                  # Test suite
├── VISION.md               # Project direction and governance intent
├── GOVERNANCE.md           # Decision-making, roles, foundation path
├── CONTRIBUTING.md         # Contribution guide
└── CHANGELOG.md            # Version history
```

---

## Contributing

Sentinel is early-stage. Useful contributions right now: test coverage, schema feedback, storage backend implementations, and compliance use case documentation. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Breaking changes to `DecisionTrace` and `StorageBackend` require an RFC.

---

## License and governance

Sentinel is released under the [Apache 2.0 License](LICENSE).

Sentinel is designed for foundation stewardship under Linux Foundation Europe. Formal engagement is planned alongside v1.0. Until then, governance decisions are made transparently through the RFC process. See [GOVERNANCE.md](GOVERNANCE.md) for the full governance model, decision-making process, and contributor path.
