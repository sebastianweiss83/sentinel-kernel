# Decision Trace Schema Reference

**Schema version:** 0.1
**Status:** Draft — subject to RFC process for breaking changes

This document is the canonical reference for the Sentinel decision trace schema.
Every trace produced by the Sentinel kernel conforms to this specification.

---

## Overview

A decision trace is a structured, immutable record of a single AI agent decision.
Traces are append-only: once written, a trace is never modified. Corrections,
overrides, and linked decisions are recorded as new trace entries referencing
the original via `parent_trace_id`.

Traces are serialised as JSON and exported as NDJSON (newline-delimited JSON).
No binary formats. No proprietary encoding.

---

## Mandatory fields

Every trace MUST contain the following fields. A trace missing any mandatory
field is invalid and MUST be rejected by the storage backend.

| Field | Type | Description | Constraints |
|---|---|---|---|
| `trace_id` | `string` | Unique identifier for this trace | Immutable after creation. ULID or UUID v4. |
| `timestamp` | `string` | When the decision was made | ISO 8601 UTC. Always present. |
| `latency_ms` | `integer` | Wall clock time of the full decision in milliseconds | Non-negative. |
| `agent` | `string` | Name of the agent or decorated function | Non-empty string. |
| `agent_version` | `string \| null` | Version of the agent | Null if version is not available. |
| `model` | `string` | Model identifier (e.g. `mistral/mistral-large-2`) | Non-empty string. |
| `model_version` | `string \| null` | Model version string | Null if version is not available. |
| `policy` | `string` | Policy name or path evaluated | Non-empty string. |
| `policy_version` | `string \| null` | Policy version | Null if policy is not versioned. |
| `policy_result` | `string` | Result of policy evaluation | One of: `ALLOW`, `DENY`, `EXCEPTION_REQUIRED`. |
| `policy_rule` | `string \| null` | The specific rule that triggered | Null only when `policy_result` is `ALLOW`. Required for `DENY` and `EXCEPTION_REQUIRED`. |
| `inputs_hash` | `string` | SHA-256 hash of serialised inputs | Format: `sha256:<hex>`. Always present. |
| `output` | `object` | The decision output | JSON-serialisable object. |
| `sovereign_scope` | `string` | Sovereignty jurisdiction assertion | One of: `EU`, `LOCAL`, `CUSTOM`. |
| `data_residency` | `string` | Where the trace is physically stored | Human-readable string (e.g. `on-premise-de`, `local`, `air-gapped`). |
| `schema_version` | `string` | Schema version of this trace | Semver string (e.g. `0.1`). |

---

## Optional fields

Optional fields MAY be present. Adding new optional fields does not require an RFC.

| Field | Type | Description |
|---|---|---|
| `parent_trace_id` | `string \| null` | Links this trace to a parent (e.g. for overrides or nested decisions). Null if top-level. |
| `inputs_raw` | `object \| null` | Raw input data. **Opt-in only.** Never included by default. Must be explicitly enabled. May contain PII — handle accordingly. |
| `override_by` | `string \| null` | Identity of the person who overrode the policy decision. Null if no override. |
| `override_reason` | `string \| null` | Justification for the override. Null if no override. |
| `override_at` | `string \| null` | ISO 8601 UTC timestamp of the override. Null if no override. |
| `tags` | `object` | Key-value metadata tags. |
| `precedent_trace_ids` | `string[]` | References to prior traces that informed this decision. |

---

## Override semantics

When a human overrides a policy decision:

1. The original trace is **never modified**.
2. A new trace entry is created with:
   - `parent_trace_id` set to the original `trace_id`
   - `override_by`, `override_reason`, and `override_at` populated
   - Its own unique `trace_id`
3. The override trace records the final policy result after human intervention.

This produces an immutable, linked chain that satisfies EU AI Act Article 14
(human oversight) requirements.

---

## Immutability constraint

**A trace is permanent once written.**

- No field may be modified after the trace is persisted.
- Storage backends MUST NOT expose update or delete operations on traces.
- Corrections are new entries referencing the original via `parent_trace_id`.
- This constraint is a legal requirement for EU AI Act Article 12 compliance
  and a prerequisite for BSI IT-Grundschutz certification.

---

## Serialisation

- **Internal:** JSON objects
- **Export:** NDJSON (one JSON object per line, newline-terminated)
- **Encoding:** UTF-8
- **No binary formats.** No proprietary encoding. No compression in the
  canonical format (compression may be applied at the transport or storage layer).

---

## Validation rules

A compliant storage backend MUST validate the following before accepting a trace:

1. `trace_id` is present and unique within the storage scope.
2. `timestamp` is a valid ISO 8601 UTC string.
3. `policy_result` is one of the three allowed values.
4. `policy_rule` is non-null when `policy_result` is `DENY` or `EXCEPTION_REQUIRED`.
5. `inputs_hash` matches the format `sha256:<64 hex characters>`.
6. `sovereign_scope` is one of: `EU`, `LOCAL`, `CUSTOM`.
7. `schema_version` is present.

---

## Schema evolution

- **Adding optional fields:** No RFC required. Backwards-compatible.
- **Adding mandatory fields:** RFC required. Must include migration path.
- **Removing or renaming fields:** RFC required. Major version bump.
- **Changing field semantics:** RFC required.

All schema changes are tracked in `schema_version`. Historical traces
can always be interpreted according to the schema version they declare.

---

## EU AI Act field mapping

| EU AI Act requirement | Satisfied by |
|---|---|
| Art. 12(1) — Automatic logging | `trace_id`, `timestamp`, `agent`, `model`, `policy_result` |
| Art. 12(2) — Risk identification | `policy_result`, `policy_rule`, queryable traces |
| Art. 13 — Transparency | `policy`, `policy_version`, `model`, `model_version` |
| Art. 14 — Human oversight | `override_by`, `override_reason`, `parent_trace_id` |
| Art. 17 — Quality management | Full trace chain, `schema_version`, append-only storage |

See [`eu-ai-act.md`](eu-ai-act.md) for the complete compliance mapping.
