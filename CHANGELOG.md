# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- `SQLiteStorage.save()` now uses `INSERT` instead of `INSERT OR REPLACE` — duplicate `trace_id` raises `IntegrityError` instead of silently overwriting. Traces are now genuinely append-only in SQLite.
- `DecisionTrace.from_dict()` now reconstructs `policy_evaluation` and `human_override` from stored JSON. Previously these were lost on deserialization.

### Added
- `tests/test_eu_ai_act_fields.py` — 12 tests verifying EU AI Act Article 12/13/14 field presence on real traces

## [0.1.0] — 2026-04-01

Initial public alpha release.

### Added
- `Sentinel` class with `@sentinel.trace` decorator (sync and async)
- `DecisionTrace` dataclass with SHA-256 input/output hashing
- `PolicyEvaluation` model with ALLOW / DENY / EXCEPTION / NOT_EVALUATED
- `HumanOverride` model for recording human intervention
- `DataResidency` enum (LOCAL, EU, EU-DE, EU-FR, air-gapped)
- `SQLiteStorage` backend — zero dependencies, works everywhere
- `FilesystemStorage` backend — NDJSON append-only, designed for air-gapped environments
- `StorageBackend` abstract interface for custom backends
- `NullPolicyEvaluator` (default), `SimpleRuleEvaluator` (Python callables), `LocalRegoEvaluator` (OPA binary)
- Trace query interface with project, agent, and policy result filters
- `sentinel.span()` async context manager for manual trace control
- Schema version 1.0.0 draft
- Documentation: schema reference, EU AI Act mapping, integration guide, BSI profile
- Apache 2.0 license

### Not yet implemented
- CLI (`sentinel` command is declared but not yet implemented)
- LangChain / LangGraph integration
- PostgreSQL storage backend
- OpenTelemetry export
- Test suite (in progress)
