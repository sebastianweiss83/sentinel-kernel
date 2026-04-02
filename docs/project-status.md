# Project Status

## Current maturity: Alpha (0.1.0)

Sentinel is in public alpha. The core interfaces are stabilising. The API will change before 1.0. Do not deploy to production systems.

---

## What "alpha" means here

- Core abstractions (`DecisionTrace`, `StorageBackend`, `PolicyEvaluator`) are taking shape but are not frozen.
- Public API may have breaking changes in any minor release before 1.0.
- The trace schema is a draft. Fields may be added, renamed, or restructured following the RFC process.
- Error handling is incomplete in some paths.
- The test suite is in progress. Coverage targets are not yet met.
- Documentation reflects intent and current behaviour, but gaps exist.

---

## What works now

| Capability | Status |
|---|---|
| `@sentinel.trace` decorator (sync and async) | Working |
| `sentinel.span()` async context manager | Working |
| `SQLiteStorage` backend | Working |
| `FilesystemStorage` backend (NDJSON append-only) | Working |
| `StorageBackend` abstract interface | Working |
| `NullPolicyEvaluator` | Working |
| `SimpleRuleEvaluator` (Python callables) | Working |
| `LocalRegoEvaluator` (OPA binary) | Working |
| Trace query with project / agent / policy result filters | Working |
| `DecisionTrace.to_dict()` / `to_json()` | Working |
| SHA-256 input and output hashing | Working |
| `HumanOverride` model | Working |
| `DataResidency` enum | Working |

---

## What is missing

| Capability | Notes |
|---|---|
| CLI (`sentinel` command) | Declared in pyproject.toml, not implemented |
| LangChain / LangGraph integration | Planned for v0.3 |
| PostgreSQL storage backend | Planned for v0.2 |
| OpenTelemetry export | Planned for v0.3 |
| `SovereigntyViolationError` enforcement | Planned for v0.3 |
| Schema migration tooling | Planned before v1.0 |

---

## API stability

Expect breaking changes before 1.0. The following are most likely to change:

- `Sentinel` constructor keyword arguments
- `StorageBackend` query interface (filter parameters and return types)
- `PolicyEvaluator` contract (particularly context passing)
- Exception hierarchy

We will document breaking changes in the [CHANGELOG](../CHANGELOG.md) and provide migration notes.

---

## Schema stability

The trace schema is at version 1.0.0 draft. The structure is intentional and unlikely to change wholesale, but individual fields may be renamed or constrained before the draft is ratified.

Changes to optional fields do not require an RFC. Changes to mandatory fields, field names, or field types require an RFC with a 14-day comment period. Breaking schema changes require a major version bump.

---

## Production-readiness disclaimer

**Do not deploy Sentinel to production systems at this stage.**

The alpha release is intended for evaluation, experimentation, and early feedback. Specifically:

- The test suite is not complete. Untested edge cases exist.
- Error handling in failure paths (storage unavailable, policy evaluator crash) has not been hardened.
- The schema is a draft and will change before 1.0.
- No security audit has been performed.

When the project reaches beta (0.2.x), we will publish a clearer statement of what is and is not safe for production use.

---

## What feedback is most useful

The most valuable input at this stage:

- **Real deployment scenarios.** What does your agent actually do? What fields are missing from the trace schema to represent it correctly?
- **Schema gaps.** Are there mandatory EU AI Act fields you need that are not present? Are field names ambiguous?
- **Storage backend needs.** What storage systems do you actually run in sovereign environments? What query patterns do you need?
- **Policy evaluation patterns.** What does a real policy look like in your organisation? Does `SimpleRuleEvaluator` cover it, or do you need something different?
- **Air-gapped constraints.** What broke when you tested without network access?

Open an issue or start a discussion on GitHub.
