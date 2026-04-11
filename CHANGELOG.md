# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.9.0] — 2026-04-11

Status: Alpha → **Beta**.

The complete Sentinel sovereignty platform. v0.9 adds the evaluation,
declaration, and verification tooling on top of the v0.4 decision
kernel. This is the release BWI and Quantum Systems design partners
are evaluating against.

### Added — v0.3b add-on: LangFuse enrichment

- **`sentinel.integrations.langfuse.LangFuseEnricher`** — attaches
  Sentinel sovereignty metadata (`sentinel.trace_id`,
  `sentinel.sovereign_scope`, `sentinel.data_residency`,
  `sentinel.policy*`) to an existing LangFuse trace via the shared
  trace id as join key. Optional extra:
  `pip install sentinel-kernel[langfuse]`.

### Added — v0.5: Sovereignty scanner

- **`sentinel.scanner.RuntimeScanner`** — classifies every installed
  Python package by parent company and jurisdiction against a
  built-in knowledge base of 80+ common AI/ML packages. Produces
  a sovereignty score and a list of critical-path violations.
- **`sentinel.scanner.CICDScanner`** — detects GitHub Actions,
  CircleCI, GitLab CI, Dockerfile base images, and docker-compose
  image references; classifies each by vendor jurisdiction.
- **`sentinel.scanner.InfrastructureScanner`** — parses Terraform
  provider blocks, Kubernetes storage classes, and `.env` file
  keys (never values) for cloud provider dependencies.
- `sentinel/scanner/knowledge.py` — conservative static mapping of
  package → parent company → jurisdiction → CLOUD Act exposure.
  Unknown is better than guessing.

### Added — v0.6: Manifesto-as-code

- **`sentinel.manifesto.SentinelManifesto`** — declare
  sovereignty requirements as a Python class. Requirement types:
  `EUOnly`, `OnPremiseOnly`, `Required`, `ZeroExposure`,
  `Targeting`, `AcknowledgedGap`.
- **`ManifestoReport`** — structured report with per-dimension
  status, gaps, acknowledged gaps, migration plans, and EU AI Act
  article checks. Exports as text, HTML, or JSON.
- `examples/manifesto_example.py` — three fictional organisations
  (defence contractor, hospital, startup) showing different
  sovereignty postures.

### Added — v0.7: EU AI Act compliance checker

- **`sentinel.compliance.EUAIActChecker`** — automated EU AI Act
  compliance check producing a `ComplianceReport`. Explicit about
  which articles are machine-checkable (Art. 9, 12, 13, 14, 17)
  vs which require human action (Art. 10, 11, 15). Honest gap
  reporting with per-article human action guidance.
- `ComplianceReport.diff()` — human-readable diff: only the gaps.
- `ComplianceReport.as_html()` — self-contained HTML suitable for
  regulatory review.

### Added — v0.8: Demo environment

- **`demo/`** — full Docker Compose stack:
  - `sentinel-demo` (demo app)
  - OpenTelemetry Collector (OTLP gRPC + Prometheus exporter)
  - Prometheus
  - Grafana with pre-provisioned "Sentinel Sovereignty" dashboard
  - Self-hosted LangFuse + PostgreSQL
- `demo/demo_app.py` — three-scenario demonstrator: procurement
  approval (Art. 9+14), LangChain-style document analysis (mocked
  LLM), sovereignty + EU AI Act report.
- `demo/grafana/dashboard-json/sovereignty.json` — live
  sovereignty dashboard with decision counts, policy distribution,
  sovereignty score, EU AI Act coverage, kill switch state, and
  enforcement countdown.

### Added — v0.9: Sovereignty dashboard + CLI

- **`sentinel.dashboard.TerminalDashboard`** — zero-dependency
  terminal dashboard using ANSI escape codes. Works in classified
  environments with no extra libraries.
- **`sentinel.dashboard.HTMLReport`** — generates a single
  self-contained HTML sovereignty report. No CDN, no external
  resource loads — grep-verified air-gapped safe.
- **`sentinel` CLI** — full command-line interface:
  - `sentinel scan [--runtime|--cicd|--infra|--all] [--json]`
  - `sentinel compliance check [--html|--json|--output PATH]`
  - `sentinel report [--output PATH] [--manifesto DOTTED:PATH]`
  - `sentinel dashboard [--frames N] [--interval S]`
  - `sentinel manifesto check DOTTED:PATH [--json]`

### Added — Ecosystem

- **`docs/ecosystem.md`** — curated registry of sovereign AI
  projects evaluated against the three sovereignty tests.
- **`docs/rfcs/RFC-001-sovereignty-manifest.md`** — draft
  specification for a cross-project sovereignty manifest standard.

### Added — Partner evaluation packages

- **`demo/bwi/`** — BWI federal evaluation package with
  `compliance_report.py` that writes `bwi_compliance_report.html`.
- **`demo/qs/`** — Quantum Systems evaluation package with
  `autonomous_decision_demo.py` — realistic VTOL mission planner
  with policy DENY, kill switch engagement, and air-gapped
  operation.

### Added — End-to-end smoke test

- `examples/smoke_test.py` rewritten to exercise the full v0.9
  stack in 16 steps. Exits 0 on success, 1 on any failure.
  Zero optional extras required. Wired into the `quickstart` CI
  job alongside the minimal and policy-deny examples.

### Changed

- `pyproject.toml` version bumped to `0.9.0`, development status
  `Alpha → Beta`.
- README roadmap table marks v0.5 through v0.9 as shipped and
  adds a "What's in v0.9" section with the sovereignty platform
  highlights.
- README gains a "Quick demo" section pointing at
  `demo/docker-compose.yml`.
- Documentation index extended with ecosystem registry, RFC-001,
  and the BWI / QS evaluation packages.

### Notes

- The `demo/` Docker Compose stack is intended for evaluation, not
  production. It pulls base images from Docker Hub; for a sovereign
  production deployment, mirror these images to an EU-sovereign
  registry (Harbor, GitLab Container Registry, or similar).
- The manifesto and compliance checker are careful to distinguish
  what can be automatically verified from what requires human
  action. This honesty is a feature, not a limitation.

## [0.4.0] — 2026-04-11

Consolidated v0.1.1 → v0.4 roadmap milestones into a single release.

### Added
- **Kill switch (v0.1.1, EU AI Act Art. 14).** `Sentinel.engage_kill_switch(reason)` / `disengage_kill_switch(reason)` / `kill_switch_active` property. When engaged, every `@sentinel.trace` call is blocked without executing the wrapped function, a DENY trace is written with a `HumanOverride` entry naming the reason, and `KillSwitchEngaged` is raised. Thread-safe via `threading.Lock`. Effective at runtime with no restart.
- **`KillSwitchEngaged` exception** exported from the top-level `sentinel` package.
- **PostgreSQL storage backend (v0.2).** `sentinel.storage.postgres.PostgresStorage`. Append-only (INSERT only, no UPDATE or DELETE), indexed on `trace_id`, `agent`, `started_at`, `policy_result`, `project`. Schema auto-created on `initialise()`. Sovereignty columns (`sovereign_scope`, `data_residency`) stored as dedicated columns. `export_ndjson()` method for portable exports. Optional extra: `pip install sentinel-kernel[postgres]`.
- **LangChain integration (v0.3).** `sentinel.integrations.langchain.SentinelCallbackHandler` — a `BaseCallbackHandler` that records a `DecisionTrace` on `on_llm_end` and `on_chain_end`, including model name, prompts, output, and latency. Uses the wrapped `Sentinel` instance's storage and sovereignty metadata. Optional extra: `pip install sentinel-kernel[langchain]`.
- **OpenTelemetry export (v0.3).** `sentinel.integrations.otel.OTelExporter` — wraps a `Sentinel` instance's storage so every `save()` also emits a `sentinel.decision` OTel span. Attributes: `sentinel.trace_id`, `sentinel.agent`, `sentinel.policy_result`, `sentinel.sovereign_scope`, `sentinel.data_residency`, `sentinel.latency_ms`, `sentinel.schema_version`. Background worker thread; failures on span export are logged and swallowed so a broken OTLP collector cannot crash the decision path. Optional extra: `pip install sentinel-kernel[otel]`.
- **Air-gapped validation suite (v0.4).** `tests/test_airgap.py` monkey-patches `socket.socket.connect` to raise on any IPv4/IPv6 connect attempt. Covers null policy, simple rule eval, local Rego (mocked), SQLite storage, Filesystem storage, full trace cycle, and kill switch — all under the network block. New CI job `airgap` runs this suite on every push.
- **End-to-end smoke test.** `examples/smoke_test.py` runs a full ALLOW / DENY / EXCEPTION / kill-switch / query / NDJSON-export cycle across SQLite and Filesystem storage. Zero extras required. Exits 0 on success. Wired into the `quickstart` CI job.
- **Tests:** +31 new tests across kill switch (6), PostgreSQL (6), LangChain (6), OTel (5), air-gap (8). Total: **102 tests**.

### Changed
- `pyproject.toml` version bumped to `0.4.0`.
- Optional extras trimmed: `langchain` now pins `langchain-core>=0.1` only (dropped `langgraph`); `postgres` pins `psycopg2-binary>=2.9` only (dropped `asyncpg`); `otel` dropped redundant `opentelemetry-api` pin.
- README roadmap table updated to mark v0.1.1 through v0.4 as shipped.

### Fixed
- `SQLiteStorage.save()` now uses `INSERT` instead of `INSERT OR REPLACE` — duplicate `trace_id` raises `IntegrityError` instead of silently overwriting. Traces are now genuinely append-only in SQLite.
- `DecisionTrace.from_dict()` now reconstructs `policy_evaluation` and `human_override` from stored JSON. Previously these were lost on deserialization.

### Notes
- The LangChain integration is provided as a convenience for teams already committed to LangChain. It is an **optional** extra and is not in the Sentinel critical path — the sovereignty check continues to pass.

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
