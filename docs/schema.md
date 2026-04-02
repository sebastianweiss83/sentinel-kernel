# Decision Trace Schema Reference

**Schema version:** 1.0.0 (draft)
**Status:** Draft — subject to RFC process for breaking changes

This document is the canonical reference for the Sentinel decision trace schema.
Every trace produced by the Sentinel kernel conforms to this specification.

---

## Overview

A decision trace is a structured record of a single AI agent decision.
Traces are serialised as JSON via `DecisionTrace.to_dict()` and exported
as NDJSON (newline-delimited JSON) by `FilesystemStorage`.

---

## Schema structure

The `DecisionTrace.to_dict()` output has this shape:

```json
{
  "schema_version": "1.0.0",
  "trace_id": "uuid-v4",
  "parent_trace_id": "uuid-v4 | null",
  "project": "string",
  "agent": "string",
  "started_at": "ISO 8601 UTC",
  "completed_at": "ISO 8601 UTC | null",
  "latency_ms": "integer | null",
  "inputs_hash": "sha256-hex (64 chars)",
  "inputs": "object (omitted if store_inputs=False)",
  "output": "object",
  "output_hash": "sha256-hex (64 chars)",
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
    "evaluated_at": "ISO 8601 UTC",
    "evaluator": "string"
  },
  "human_override": {
    "override_id": "uuid-v4",
    "approver_id": "string",
    "approver_role": "string",
    "justification": "string",
    "approved_at": "ISO 8601 UTC"
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

Notes:
- `policy` is `null` when no policy evaluator is configured (the default `NullPolicyEvaluator` still produces a `PolicyEvaluation` with `result: NOT_EVALUATED` when a policy path is specified via the decorator).
- `human_override` is `null` unless `add_override()` is called on the trace.
- `model` fields are `null` unless explicitly set — Sentinel does not auto-detect which model was called.

---

## Top-level fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | `string` | Always `"1.0.0"` in this release. |
| `trace_id` | `string` | UUID v4, generated at trace creation. Unique per trace. |
| `parent_trace_id` | `string \| null` | Links to a parent trace (for overrides or chained decisions). |
| `project` | `string` | Project name, set at `Sentinel` initialisation. Default: `"default"`. |
| `agent` | `string` | Name of the decorated function (from `__qualname__`), or the `agent_name` kwarg. |
| `started_at` | `string` | ISO 8601 UTC timestamp when the trace was created. |
| `completed_at` | `string \| null` | ISO 8601 UTC timestamp when `complete()` was called. `null` if trace is incomplete. |
| `latency_ms` | `integer \| null` | Wall clock milliseconds for the wrapped function execution. |
| `inputs_hash` | `string` | SHA-256 hex digest of the JSON-serialised inputs. Always computed when inputs are present. |
| `inputs` | `object` | The captured function arguments. Empty `{}` if `store_inputs=False`. |
| `output` | `object` | The function return value (must be a dict, or wrapped as `{"result": repr(value)}`). |
| `output_hash` | `string` | SHA-256 hex digest of the JSON-serialised output. |
| `tags` | `object` | User-provided key-value metadata, set via `@sentinel.trace(tags={...})`. |
| `precedent_trace_ids` | `string[]` | References to prior traces that informed this decision. Set via `link_precedent()`. |

---

## `model` object

| Field | Type | Description |
|---|---|---|
| `provider` | `string \| null` | Model provider identifier. Must be set explicitly. |
| `name` | `string \| null` | Model name. Must be set explicitly. |
| `version` | `string \| null` | Model version string. |
| `tokens_input` | `integer \| null` | Input token count, if available. |
| `tokens_output` | `integer \| null` | Output token count, if available. |

These fields are `null` by default. Sentinel does not auto-detect model metadata. Future framework integrations may populate these automatically.

---

## `policy` object

Present when a `PolicyEvaluator` produces a `PolicyEvaluation`. `null` when no policy path is specified in the decorator and no evaluator is configured.

| Field | Type | Description |
|---|---|---|
| `policy_id` | `string` | The policy path passed to `@sentinel.trace(policy="...")`. |
| `policy_version` | `string` | Version string from the evaluator (e.g. `"python-callable"`, `"null"`, or a hash). |
| `result` | `string` | One of: `ALLOW`, `DENY`, `EXCEPTION`, `NOT_EVALUATED`. |
| `rule_triggered` | `string \| null` | Which rule caused a DENY. `null` on ALLOW or NOT_EVALUATED. |
| `rationale` | `string \| null` | Human-readable explanation from the evaluator. |
| `evaluated_at` | `string` | ISO 8601 UTC timestamp of evaluation. |
| `evaluator` | `string` | Identifier of the evaluator implementation (e.g. `"sentinel-opa"`, `"sentinel-simple"`). |

---

## `human_override` object

Present when `trace.add_override(HumanOverride(...))` is called. `null` otherwise.

| Field | Type | Description |
|---|---|---|
| `override_id` | `string` | UUID v4, auto-generated. |
| `approver_id` | `string` | Identity of the approver. Required. |
| `approver_role` | `string` | Role of the approver. Required. |
| `justification` | `string` | Reason for the override. Required. |
| `approved_at` | `string` | ISO 8601 UTC timestamp. |

---

## `sovereignty` object

| Field | Type | Description |
|---|---|---|
| `data_residency` | `string` | Value of the `DataResidency` enum: `local`, `EU`, `EU-DE`, `EU-FR`, or `air-gapped`. |
| `sovereign_scope` | `string` | Free-text sovereignty scope, set at `Sentinel` initialisation. Default: `"local"`. |
| `storage_backend` | `string` | Name of the storage backend (e.g. `"sqlite"`, `"filesystem"`). |

---

## Hashing

- `inputs_hash` and `output_hash` are SHA-256 hex digests (64 characters).
- Computed over `json.dumps(data, sort_keys=True, default=str)`.
- No `sha256:` prefix in the current implementation — the field contains the raw hex string.
- Hashing is automatic when inputs or output are set.

---

## Serialisation

- **In-memory:** `DecisionTrace` Python dataclass
- **JSON:** `trace.to_dict()` returns a Python dict; `trace.to_json()` returns formatted JSON
- **Export:** `FilesystemStorage` writes NDJSON (one JSON object per line)
- **Encoding:** UTF-8

---

## Schema evolution

- **Adding optional fields:** No RFC required. Backwards-compatible.
- **Adding mandatory fields:** RFC required. Must include migration path.
- **Removing or renaming fields:** RFC required. Major version bump.
- **Changing field semantics:** RFC required.

All schema changes are tracked in `schema_version`. Historical traces
can always be interpreted according to the schema version they declare.

---

## Known limitations (v0.1.0)

- `model` fields must be set manually. No auto-detection from framework integrations exists yet.
- `FilesystemStorage` does not enforce uniqueness on `trace_id` — duplicate writes append a second line. Deduplication is the caller's responsibility.

---

## EU AI Act field mapping

| EU AI Act requirement | Satisfied by |
|---|---|
| Art. 12(1) — Automatic logging | `trace_id`, `started_at`, `agent`, `model`, `policy.result` |
| Art. 12(2) — Risk identification | `policy.result`, `policy.rule_triggered`, queryable traces |
| Art. 13 — Transparency | `policy.policy_id`, `policy.policy_version`, `model` |
| Art. 14 — Human oversight | `human_override`, `parent_trace_id` |
| Art. 17 — Quality management | Full trace chain, `schema_version`, storage persistence |

See [`eu-ai-act.md`](eu-ai-act.md) for the complete compliance mapping.
