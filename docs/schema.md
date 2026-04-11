# Sentinel trace schema — v1.0.0

Every decision trace produced by Sentinel follows this schema. The schema is versioned. Breaking changes require an RFC and a 14-day comment period.

## Mandatory fields

All fields below are present in every trace. Fields marked `nullable` are present but may be `null` under specified conditions.

```json
{
  "trace_id":       "string  — ULID, immutable after creation",
  "parent_trace_id":"string? — ULID of parent trace; null if top-level",
  "timestamp":      "string  — ISO 8601 UTC, e.g. 2026-04-01T14:23:41.234Z",
  "latency_ms":     "integer — wall clock time of full decision in milliseconds",

  "agent":          "string  — name of the agent or function",
  "agent_version":  "string? — version string; null if unavailable",

  "model":          "string  — model identifier, e.g. mistral/large-2",
  "model_version":  "string? — model version; null if unavailable",

  "policy":         "string  — policy name",
  "policy_version": "string? — policy version; null if policy is unversioned",
  "policy_result":  "string  — ALLOW | DENY | EXCEPTION_REQUIRED",
  "policy_rule":    "string? — name of the rule that triggered; null if ALLOW",

  "inputs_hash":    "string  — SHA-256 of serialised inputs, always present",
  "inputs_raw":     "object? — raw inputs; opt-in only, never present by default",
  "output":         "object  — the decision output",

  "override_by":    "string? — identity of human who overrode; null if no override",
  "override_reason":"string? — reason stated; null if no override",
  "override_at":    "string? — ISO 8601 UTC timestamp of override; null if no override",

  "sovereign_scope":"string  — EU | LOCAL | CUSTOM",
  "data_residency": "string  — human-readable assertion of where the trace is stored",
  "schema_version": "string  — schema version, always 1.0.0 for this schema"
}
```

## Immutability

A trace is never edited after creation. Corrections and overrides are new trace entries referencing the original via `parent_trace_id`. This is a legal requirement for EU AI Act Art. 12 compliance.

## Override pattern

When a human overrides a decision, Sentinel records a second trace entry:

```json
{
  "trace_id":       "new ULID",
  "parent_trace_id":"ULID of original trace",
  "override_by":    "operator@example.eu",
  "override_reason":"Manual review completed — approved under delegated authority",
  "override_at":    "2026-04-01T14:31:17.891Z",
  ...all other fields from the original decision...
}
```

The original trace is unchanged.

## Export format

Traces are exported as NDJSON (newline-delimited JSON): one JSON object per line. This format is:
- Streamable (no need to load the entire file)
- Appendable (new traces append to the file)
- Portable (no proprietary encoding)
- Compatible with standard log analysis tools

## Schema changes

Adding optional fields: no RFC required. Announce in changelog.
Removing or renaming fields: RFC required. 14-day comment period. Major version bump.
Adding mandatory fields: RFC required. 14-day comment period. Major version bump.
