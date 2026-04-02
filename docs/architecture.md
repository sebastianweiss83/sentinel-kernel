# Architecture

**Status:** Living document
**Last updated:** April 2026
**Authors:** Sentinel maintainers

This document defines the architectural principles and key decisions of the Sentinel kernel. All contributions are evaluated against it. Changes to the core architecture require an RFC with a 14-day comment period.

---

## Kernel responsibilities

Sentinel does one thing: sit in the execution path of AI agent calls and emit sovereign decision traces.

It does not:
- Host a dashboard
- Train models
- Manage prompt templates
- Replace systems of record
- Provide a model serving layer

If a proposed feature is not directly in service of capturing a decision trace, it belongs in a separate project.

---

## Trace lifecycle

```
1. CREATE       Sentinel intercepts the call. A DecisionTrace is initialised
                with trace_id, parent_trace_id, project, agent, started_at,
                inputs_hash (and optionally inputs).

2. POLICY EVAL  The configured PolicyEvaluator runs before the wrapped
                function executes. Result is ALLOW, DENY, EXCEPTION, or
                NOT_EVALUATED (NullPolicyEvaluator).

                If DENY: PolicyDeniedError is raised. The trace is written
                with policy.result = DENY. The wrapped function never runs.

3. EXECUTE      On ALLOW or NOT_EVALUATED: the wrapped function runs.
                Sentinel captures the return value.

4. COMPLETE     completed_at, latency_ms, output, and output_hash are
                written to the trace. Any exception from the wrapped
                function is recorded and re-raised.

5. PERSIST      The completed DecisionTrace is written to the configured
                StorageBackend. Write failures are not silenced — a missing
                trace is worse than a crash.
```

---

## Policy evaluation contract

A `PolicyEvaluator` receives a `policy_path`, the `inputs` dict, and the current `DecisionTrace`. It returns a `PolicyEvaluation` with:

- `result` — ALLOW / DENY / EXCEPTION / NOT_EVALUATED
- `rule_triggered` — which rule caused a DENY (required on DENY, null otherwise)
- `rationale` — optional human-readable explanation
- `policy_id` and `policy_version` — for audit provenance

The evaluator must not modify inputs. It must not have side effects.

Three implementations ship with the kernel:

| Evaluator | Description |
|---|---|
| `NullPolicyEvaluator` | Default. Records NOT_EVALUATED. Suitable for bootstrapping. |
| `SimpleRuleEvaluator` | Wraps a Python callable. No dependencies. |
| `LocalRegoEvaluator` | Shells out to a local OPA binary. Zero network. |

---

## Storage abstraction

`StorageBackend` is an abstract class with four methods: `initialise()`, `save(trace)`, `query(project, agent, policy_result, limit, offset)`, and `get(trace_id)`. No implementation is privileged.

Two implementations ship with the kernel:

| Backend | Description |
|---|---|
| `SQLiteStorage` | Uses stdlib `sqlite3`. Zero dependencies. Works everywhere. |
| `FilesystemStorage` | NDJSON, append-only, one file per day. Designed for air-gapped environments. |

Custom backends implement `StorageBackend`. Adding a new backend requires no changes to the kernel core.

The `query()` interface supports filtering by `project`, `agent`, and `policy_result`. Richer query capabilities (time range, tag filters, full-text) are deferred to later versions and will be shaped by real deployment feedback.

---

## Optional integrations vs critical path

The critical path — trace creation, policy evaluation, storage write — has zero mandatory dependencies. It runs with Python's standard library alone.

Everything else is optional and must be installed explicitly:

```
pip install sentinel-kernel[langchain]   # LangChain integration (planned v0.3)
pip install sentinel-kernel[postgres]    # PostgreSQL backend (planned v0.2)
pip install sentinel-kernel[otel]        # OpenTelemetry export (planned v0.3)
```

Optional integrations may depend on US-incorporated services or third-party packages. They are clearly labelled as non-sovereign where applicable. They must never appear in the critical path.

---

## Offline / air-gapped design

Every feature is tested against the most constrained deployment target: no network, local storage only.

Air-gapped operation constraints:
- `SQLiteStorage` and `FilesystemStorage` make no network calls.
- `NullPolicyEvaluator` and `SimpleRuleEvaluator` make no network calls.
- `LocalRegoEvaluator` requires a local OPA binary — no OPA cloud, no network.
- The `sentinel-kernel` package itself must be installable from a local mirror or vendored.

If a proposed feature requires a network call in the default configuration, it is not complete. It belongs in an optional extra.

---

## What the kernel will never include

- A hosted SaaS service (that is a commercial product built on top of the kernel)
- A proprietary dashboard (build one with the query API)
- A model serving layer (use a local inference server)
- A prompt management system (use a dedicated tool)
- A fine-tuning pipeline

These belong elsewhere. The kernel stays small.

---

## Architecture principles

### Principle 1: Standard formats, always

Traces are stored as NDJSON. Policies are OPA Rego or Python callables. The trace schema is defined in this repository and versioned explicitly.

Proprietary trace formats create switching costs. When a standard exists — NDJSON, ISO 8601, SHA-256, OpenTelemetry — use it. We do not invent serialisation formats, query languages, or policy syntaxes.

### Principle 2: Zero hard dependencies

The `sentinel-kernel` package installs with zero mandatory dependencies. Everything is optional.

Classified and air-gapped environments cannot run arbitrary dependency chains. A regulated environment's security team must be able to audit every package. The kernel works with Python's standard library alone.

### Principle 3: Pluggable everything

Storage, policy evaluation, and LLM provider are interfaces with multiple implementations. No implementation is privileged.

Deployment environments vary enormously: on-premise databases, air-gapped filesystems, sovereign edge storage, custom audit systems not built yet. The kernel owns orchestration logic and delegates storage and policy to implementations. New backends require no changes to core.

### Principle 4: Sovereignty is a data residency assertion, not a feature

Every `DecisionTrace` carries a `data_residency` field and a `sovereign_scope` field, set at `Sentinel` initialisation time and propagated to every trace.

Sovereignty cannot be bolted on after the fact. If an environment is configured for `DataResidency.EU_DE`, every trace carries that assertion — meaning auditors can query by sovereignty scope and know the assertion was made at infrastructure configuration time, not added to a report post-hoc.

`DataResidency` is a first-class enum, not a tag. Enforcement of residency constraints at write time (raising `SovereigntyViolationError` when a trace configured for `EU_DE` is sent to a non-sovereign backend) is planned for v0.3.

### Principle 5: Human overrides are first-class events

A `HumanOverride` is a first-class model in the trace schema, not a tag or comment.

An override is a significant event in a decision chain: it records an exception to policy and establishes precedent. Logging it as a generic tag loses the approver identity, justification, timestamp, and linkage to the originating policy denial. A first-class model preserves all of this and makes overrides queryable.

`HumanOverride` has required fields: `approver_id`, `approver_role`, `justification`. Overrides cannot be anonymous.

### Principle 6: Ship small, iterate fast

v0.1 ships with SQLite storage, filesystem storage, null policy evaluator, simple Python-callable evaluator, and the `@sentinel.trace` decorator. Nothing else.

Projects that become standards ship a kernel that works immediately, then let real deployment feedback drive the roadmap. The test suite, framework integrations, and additional backends are shaped by deployed users and design partners. The issue tracker is not the roadmap.

---

## Trace schema v1.0.0 (draft)

```json
{
  "schema_version": "1.0.0",
  "trace_id": "uuid-v4",
  "parent_trace_id": "uuid-v4 | null",
  "project": "string",
  "agent": "string",
  "started_at": "ISO 8601",
  "completed_at": "ISO 8601 | null",
  "latency_ms": "integer | null",
  "inputs_hash": "sha256-hex",
  "inputs": "object (omitted if store_inputs=False)",
  "output": "object",
  "output_hash": "sha256-hex",
  "model": {
    "provider": "string | null",
    "name": "string | null",
    "version": "string | null",
    "tokens_input": "integer | null",
    "tokens_output": "integer | null"
  },
  "policy": {
    "policy_id": "string",
    "policy_version": "string",
    "result": "ALLOW | DENY | EXCEPTION | NOT_EVALUATED",
    "rule_triggered": "string | null",
    "rationale": "string | null",
    "evaluated_at": "ISO 8601",
    "evaluator": "string"
  },
  "human_override": {
    "override_id": "uuid-v4",
    "approver_id": "string",
    "approver_role": "string",
    "justification": "string",
    "approved_at": "ISO 8601"
  },
  "sovereignty": {
    "data_residency": "local | EU | EU-DE | EU-FR | air-gapped",
    "sovereign_scope": "string",
    "storage_backend": "string"
  },
  "tags": "object<string, string>",
  "precedent_trace_ids": "string[]"
}
```

A concrete example trace is available at [trace-example.json](trace-example.json).

Schema changes require a version bump and a documented migration path. Breaking changes require a major version bump and an RFC.
