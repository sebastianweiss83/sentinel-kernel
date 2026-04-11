# Architecture overview (BSI pre-engagement)

## The five layers

```
                     ┌──────────────────────────────────┐
                     │  1. Interceptor                    │
                     │     @sentinel.trace decorator      │
                     │     wraps any Python callable      │
                     └──────────────┬───────────────────┘
                                    │
                     ┌──────────────▼───────────────────┐
                     │  2. Policy evaluator               │
                     │     SimpleRule | LocalRego | custom│
                     │     returns ALLOW / DENY / EXC     │
                     └──────────────┬───────────────────┘
                                    │
                     ┌──────────────▼───────────────────┐
                     │  3. DecisionTrace data model       │
                     │     frozen dataclass, SHA-256 hash │
                     │     all mandatory fields present   │
                     └──────────────┬───────────────────┘
                                    │
                     ┌──────────────▼───────────────────┐
                     │  4. Storage backend (in critical   │
                     │     path — always synchronous)     │
                     │     SQLite | Filesystem | Postgres │
                     │     append-only                     │
                     └──────────────┬───────────────────┘
                                    │
                     ┌──────────────▼───────────────────┐
                     │  5. Optional exporters (additive,  │
                     │     never gate the critical path)  │
                     │     OTel · LangFuse · Prometheus   │
                     └──────────────────────────────────┘
```

## Load-bearing properties

1. **Storage is always first.** Every optional exporter runs
   *after* the local write has succeeded. A hostile or broken
   exporter cannot drop a trace.
2. **The critical path is offline.** Neither the decorator, the
   policy evaluator, nor the storage write makes a network call
   in the default configuration. CI proves this on every PR.
3. **Every trace is immutable after write.** Storage backends
   expose no `UPDATE` or `DELETE` methods on traces. Corrections
   are new linked traces, not mutations.
4. **Every trace is verifiable.** `Sentinel.verify_integrity()`
   recomputes SHA-256 on the stored inputs and outputs and
   compares with the stored hashes.
5. **Kill switch halts everything instantly.** `engage_kill_switch`
   flips a thread-safe flag; every subsequent `@sentinel.trace`
   call produces a DENY trace with a linked `HumanOverride`.

## Schema (simplified)

```json
{
  "trace_id": "...",
  "parent_trace_id": null,
  "project": "my-agent",
  "agent": "approve",
  "started_at": "2026-04-11T13:00:00+00:00",
  "completed_at": "2026-04-11T13:00:00+00:00",
  "latency_ms": 3,
  "inputs_hash": "sha256:...",
  "output_hash": "sha256:...",
  "policy": {
    "policy_id": "policies/approval.py",
    "policy_version": "1.0.0",
    "result": "ALLOW",
    "rule_triggered": null,
    "evaluator": "sentinel-simple"
  },
  "sovereignty": {
    "data_residency": "EU-DE",
    "sovereign_scope": "EU",
    "storage_backend": "sqlite"
  },
  "schema_version": "1.0.0"
}
```

Full field reference: `docs/schema.md`.

## What a reviewer verifies

1. The trace shape: every BSI-relevant field is present.
2. The critical-path behaviour: the storage write happens before
   any optional exporter.
3. The kill-switch behaviour: `engage_kill_switch` is observable
   in subsequent traces.
4. The integrity check: `verify_integrity` re-hashes and compares.
5. The air-gap posture: `tests/test_airgap.py` is a deterministic
   reproducer of the offline promise.
