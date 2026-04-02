# Protocol Conventions — Decision Trace Schema

## Mandatory fields
```
trace_id          Unique. Immutable after creation.
parent_trace_id   For nested decisions. Null if top-level.
timestamp         ISO 8601 UTC.
latency_ms        Wall clock time of the full decision.
agent             Name of the agent or function.
agent_version     Version string. Null if unavailable.
model             Model identifier.
model_version     Version. Null if unavailable.
policy            Policy name.
policy_version    Policy version. Null if not versioned.
policy_result     ALLOW | DENY | EXCEPTION_REQUIRED.
policy_rule       Rule that triggered. Null only if ALLOW.
inputs_hash       SHA-256 of serialised inputs. Always present.
inputs_raw        Raw inputs. Opt-in only. Never default.
output            The decision output.
override_by       Who overrode. Null if no override.
override_reason   Reason. Null if no override.
override_at       Timestamp. Null if no override.
sovereign_scope   EU | LOCAL | CUSTOM.
data_residency    Where the trace is stored. Human-readable.
schema_version    Schema version.
```

## Immutability
A trace is never edited. Corrections and overrides are new entries.

## Portability
Traces export as NDJSON. No binary formats. No proprietary encoding.

## Schema changes
Optional fields: no RFC required.
Removing/renaming or new mandatory fields: RFC required.
