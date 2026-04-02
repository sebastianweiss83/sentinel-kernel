# Architecture Decision Record

**Status:** Living document  
**Last updated:** April 2026  
**Authors:** Sentinel maintainers

This document defines the architectural principles and key decisions of the Sentinel kernel. All contributions are evaluated against it. Changes to the core architecture require an RFC with a 14-day comment period.

---

## The single job

Sentinel does one thing: **sit in the execution path of AI agent calls and emit sovereign decision traces**.

It does not:
- Host a dashboard
- Train models
- Manage prompt templates
- Compete with LangGraph, CrewAI, or AutoGen
- Replace systems of record

If a proposed feature is not directly in service of capturing a decision trace, it belongs in a separate project.

---

## Principle 1: Standard formats, always

**Decision:** Traces are OpenTelemetry spans with Sentinel semantic conventions. Storage is NDJSON. Policies are OPA Rego (or Python callables as an entry point).

**Rationale:** Proprietary trace formats create lock-in. If Sentinel defines its own format, every enterprise that adopts it has an eventual switching cost back to Sentinel. By using OTEL, traces flow naturally into Datadog, Grafana, Jaeger, Honeycomb, and any future tooling. Enterprises already have OTEL infrastructure.

**Consequence:** We never invent a new serialisation format, query language, or policy syntax. When a standard exists, we use it.

---

## Principle 2: Zero hard dependencies

**Decision:** The `sentinel-kernel` package installs with zero mandatory dependencies. Everything is optional.

**Rationale:** Classified and air-gapped environments cannot run arbitrary pip install chains. A regulated enterprise's security team must be able to audit every dependency. The kernel must work with Python's standard library alone.

**Consequence:** SQLite backend uses the stdlib `sqlite3` module. Filesystem backend uses `pathlib` and `json`. Optional extras (`[anthropic]`, `[langchain]`, `[postgres]`) are installed explicitly.

---

## Principle 3: Pluggable everything

**Decision:** Storage, policy evaluation, and LLM provider are all interfaces with multiple implementations. No implementation is privileged.

**Rationale:** An enterprise in Munich may run Postgres on-prem. An autonomous system company may run air-gapped filesystem. A startup may use a sovereign edge database. A classified deployment may need a custom backend we haven't built yet. The kernel must be agnostic.

**Consequence:** `StorageBackend`, `PolicyEvaluator`, and LLM client are abstract interfaces. The kernel owns the orchestration logic; it delegates storage, policy, and LLM to implementations. New backends require no changes to core.

---

## Principle 4: Sovereignty is a data residency assertion, not a feature

**Decision:** Every `DecisionTrace` carries a `data_residency` field and a `sovereign_scope` field, set at Sentinel initialisation time and propagated to every trace.

**Rationale:** Sovereignty cannot be bolted on after the fact. If an enterprise configures `DataResidency.EU_DE`, every trace produced by that instance carries that assertion — meaning auditors can query by sovereignty scope and know that the assertion was set at infrastructure configuration time, not post-hoc in a governance report.

**Consequence:** `DataResidency` is a first-class enum, not a tag. Attempting to store a trace configured for `EU_DE` in a US-hosted backend should raise a `SovereigntyViolationError` (planned for v0.3).

---

## Principle 5: Human overrides are first-class events

**Decision:** A `HumanOverride` is a first-class model in the trace schema, not a tag or a comment.

**Rationale:** The Foundation Capital context graph thesis rests on decision traces capturing not just what happened but why it was allowed to happen — specifically exceptions. An override is the most important event in a decision chain: it establishes precedent. If we log it as a tag (`{"override": "true"}`), we lose the approver, the justification, the timestamp, and the linkage to the originating policy denial. A first-class model preserves all of this.

**Consequence:** `HumanOverride` has required fields: `approver_id`, `approver_role`, `justification`. Overrides cannot be anonymous.

---

## Principle 6: Ship small, iterate fast

**Decision:** v0.1 ships with: SQLite storage, filesystem storage, null policy evaluator, simple Python-callable evaluator, and the `@sentinel.trace` decorator. Nothing else.

**Rationale:** The projects that become standards ship a kernel that works immediately, then let real deployment feedback drive the roadmap. Building LangGraph integration, the OPA evaluator, and Postgres backend before anyone is using the kernel is waste. Design partner deployments shape v0.2. The community shapes v0.3.

**Consequence:** We say no to every feature that doesn't serve a deployed user. The issue tracker is not the roadmap.

---

## Trace schema v1.0.0

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

Schema changes require a version bump and a migration path. Breaking changes require a major version bump and an RFC.

---

## What we will never build into the kernel

- A hosted SaaS service (that's a commercial product built on top)
- A proprietary dashboard (build one with the query API)
- A model serving layer (use Ollama, vLLM, or any provider)
- A prompt management system (use Langfuse, PromptLayer, or similar)
- A fine-tuning pipeline

These belong elsewhere. The kernel stays small.
