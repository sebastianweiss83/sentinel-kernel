# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [2.4.0] — 2026-04-11

**Rust RFC-001 implementation. Closes #13. Multi-language spec.**

### Added

- **`rust-impl/`** — Rust implementation of RFC-001
  SovereigntyManifest (`sentinel-manifest` crate). Mirrors the Python
  reference API. Runnable via `cargo run --example basic`.
- **`.github/workflows/rust.yml`** — `cargo fmt`, `cargo clippy -D warnings`,
  `cargo test --all-targets` on every PR that touches `rust-impl/`.
- **RFC-001 Implementations table** — documents Python reference
  (stable) and Rust (v0.1.0). Go and TypeScript are wanted.

## [2.3.0] — 2026-04-11

**LangFuse sovereignty panel. Closes #14.**

### Added

- **`LangFuseEnricher.create_sovereignty_widget(sentinel)`** — generate
  a self-contained HTML sovereignty widget for LangFuse custom panels.
  No CDN, no external resources. SVG gauge, kill switch status,
  EU AI Act coverage bars, trace counts.
- **`generate_langfuse_panel(sentinel)`** — module-level function for
  standalone use without a full LangFuse client.

## [2.2.0] — 2026-04-11

**Quantum-safe trace signing.**

### Added

- **`QuantumSafeSigner`** — ML-DSA-65 (FIPS 204) trace signing via
  the `sentinel-kernel[pqc]` optional extra. Keys stored operator-side,
  never on external servers. BSI TR-02102-1 compliant algorithm.
- **`RFC3161Timestamper`** — timestamping via EU-sovereign TSAs only
  (DFN-CERT, D-Trust). Rejects US-based TSAs at construction time.
  Air-gap fallback: local timestamp when network is unavailable.
- **`sentinel keygen`** CLI — generate `signing.key` / `signing.pub`
  without ever printing key material. Private key mode set to 0600.
- **`Sentinel(signer=...)`** parameter — every trace is signed
  in-process before storage. Signature fields added to
  `DecisionTrace`: `signature`, `signature_algorithm`.
- **BSI TR-02102-1 algorithm compliance** documented in
  `docs/bsi-profile.md`.

## [2.1.0] — 2026-04-11

**Sovereign-first governance primitives.**

### Added

- **`BudgetTracker`** — client-side spend tracking with a sovereign
  audit trail. Every cost entry is a local `DecisionTrace`. No
  external service, no API key, works air-gapped.
- **`Sentinel.preflight(action_type)`** — check if an action would
  be allowed before executing it. No trace written. Returns instantly.
- **Output verification** — `Sentinel.verify_output(trace_id, output)`
  and `DecisionTrace.verify_output(output)` compare a value against
  a recorded `output_hash`. Works offline.
- **Attestations** — `generate_attestation()` / `verify_attestation()`
  produce portable, self-contained governance JSON documents whose
  SHA-256 hash is the proof. Verifiable offline, no cloud needed.
- **`sentinel attestation`** CLI — `generate` and `verify` subcommands.
- **`SentinelCrewCallback`** — CrewAI task callback integration
  (`pip install sentinel-kernel[crewai]`).
- **`SentinelAutoGenHook`** — Microsoft AutoGen agent hook integration
  (`pip install sentinel-kernel[autogen]`).
- **Manifesto 5 theses as named CI checks** — new `manifesto-checks`
  job runs Thesis 1 (no US-owned deps), Thesis 2 (air-gap), Thesis 3
  (`check_license.py`), Thesis 4 (`check_manifesto.py`), Thesis 5
  (trace immutability).
- **GitHub community health files** — issue templates (bug, feature,
  integration), PR template, `FUNDING.yml`, README star CTA.
- **`docs/preview/data.json`** — live metrics emitted on every sync
  for GitHub Pages consumers.

### Changed

- `sentinel demo` now prints the attestation and report commands
  at the end, plus a subtle star CTA.
- Runtime scanner's optional-extras allowlist now includes
  `langsmith` (transitive dep of optional `langchain`/`langfuse`).

## [2.0.0] — 2026-04-11

**Major release. Production stable. BSI assessment ready.**

No breaking changes. v2.0 freezes the v1.x API surface under
SemVer guarantees and ships three v2.0-specific documents that
prepare the codebase for formal BSI IT-Grundschutz assessment.

### Added

- **`docs/api-stability.md`** — every public API classified as
  STABLE, BETA, or EXPERIMENTAL. Breaking changes to STABLE APIs
  now require a major version bump.
- **`docs/migration-v2.md`** — v1.x → v2.0 migration guide.
  Short answer: no breaking changes, just upgrade the pin.
- **`docs/bsi-pre-engagement/`** — complete 4-document package
  ready for the first BSI meeting:
  - `README.md` — what and why
  - `technical-summary.md` — 2-page project summary
  - `architecture-overview.md` — the 5-layer architecture
  - `test-evidence.md` — the test suite as BSI evidence
  - `ai-act-mapping.md` — Art. 12/13/14 mapping with
    file-and-line references into the implementation

### Changed

- **Status:** Production/Stable. This is explicit in the
  classifiers in `pyproject.toml` and the release notes.
- **Coverage baseline:** 100% line coverage is now the
  release-blocking standard. Every module in `sentinel/` sits
  at 100%.
- **Test count:** 503+ tests across unit, integration,
  compliance, and air-gap suites.

### Deprecated

Nothing. Every v1.x API is preserved.

### Roadmap beyond v2.0

- **2026-Q2** — first BSI pre-engagement meeting
- **2026-Q3** — design partner pilot in production
- **2026-Q4** — formal BSI assessment begins; LF Europe
  application submitted
- **2027-Q1** — VS-NfD profile iteration

## [1.9.0] — 2026-04-11

Minor release. Advanced compliance — DORA and NIS2 checkers with
a unified compliance command.

### Added

- **`DoraChecker`** — `sentinel.compliance.dora.DoraChecker`. Maps
  DORA Art. 6, 17, 24, 28 to Sentinel capabilities. EU Regulation
  2022/2554, in force since 2025-01-17.
- **`NIS2Checker`** — `sentinel.compliance.nis2.NIS2Checker`. Maps
  NIS2 Art. 20, 21, 23, 24 to Sentinel capabilities. EU Directive
  2022/2555, transposition deadline 2024-10-17.
- **`UnifiedComplianceChecker`** — runs EU AI Act + DORA + NIS2
  in one call, with per-framework flags (`financial_sector=True`,
  `critical_infrastructure=True`). HTML/JSON/text output.
- **`sentinel dora check` / `sentinel nis2 check` CLI commands**.
- **`sentinel compliance check --all-frameworks`** — runs every
  applicable framework at once. Also `--financial-sector` and
  `--critical-infrastructure` flags.
- **`docs/dora-compliance.md`** and **`docs/nis2-compliance.md`** —
  framework-specific mapping documents.

### Notes

- 503 tests passing, 100% coverage maintained.
- Each checker is honest about the automated-vs-operator split —
  articles that inherently require human action are marked
  `ACTION_REQUIRED` with a short explanation.

## [1.8.0] — 2026-04-11

Minor release. Developer experience — Jupyter notebook widget,
FastAPI middleware, Django middleware.

### Added

- **Jupyter integration** — `sentinel.integrations.jupyter.SentinelWidget`.
  Live decision feed in a notebook cell. `refresh()` manual update,
  `display()` renders inline. Optional extra: `pip install sentinel-kernel[jupyter]`.
- **FastAPI middleware** — `sentinel.integrations.fastapi.SentinelMiddleware`.
  Starlette-based, traces every request, skips health/metrics
  endpoints automatically, optional `path_prefixes` filter. Optional
  extra: `pip install sentinel-kernel[fastapi]`.
- **Django middleware** — `sentinel.integrations.django.SentinelMiddleware`.
  New-style callable, reads `settings.SENTINEL`, raises
  `ImproperlyConfigured` when not configured. Optional extra:
  `pip install sentinel-kernel[django]`.
- **Jupyter + FastAPI + Django dev deps** — pulled into the `[dev]`
  extra so CI exercises every middleware path.

### Notes

- 468 tests passing, 100% coverage maintained.
- All three integrations follow the same structure as the existing
  LangChain / Haystack / OTel / LangFuse integrations: guarded
  `ImportError` with a helpful message naming the extra.

## [1.7.0] — 2026-04-11

Minor release. Production hardening — trace integrity, retention,
policy versioning, and performance benchmarks.

### Added

- **Trace integrity verification** — `Sentinel.verify_integrity(trace_id)`
  recomputes `inputs_hash` and `output_hash` from stored payloads and
  compares with the stored hashes. Returns a structured
  `IntegrityResult`. This is the feature that makes Sentinel
  defensible in court: every trace can be independently verified as
  unmodified.
- **`sentinel verify` CLI command** — `--trace-id <id>`, `--all`,
  `--json`. Exits 1 when any trace fails verification.
- **Retention purge** — `StorageBackend.purge_before(cutoff, dry_run=True)`
  with `PurgeResult(traces_affected, oldest_remaining, dry_run)`.
  Defaults to dry-run so accidents are impossible.
- **`sentinel purge --before <date>` CLI command** — `--dry-run`
  (default), `--yes` to actually delete.
- **`PolicyVersion` dataclass** — immutable metadata with SHA-256 of
  the policy source, effective dates, and a name. Factory methods
  `from_callable` and `from_file`.
- **Performance benchmarks** — `benchmarks/benchmark_trace.py` with
  five metrics: SQLite in-memory, SQLite on-disk, Filesystem,
  decorator overhead, memory per 1000 traces. `--regress-check`
  exits 1 when any metric is >20% below baseline.
- **`docs/performance.md`** — documented baselines and profiling
  guidance.

### Notes

- 448 tests passing, 100% coverage maintained.
- `SQLiteStorage._delete_traces` is the reference delete path;
  filesystem and postgres backends raise `NotImplementedError` on
  `_delete_traces` until explicit retention support is added.

## [1.6.0] — 2026-04-11

Minor release. VS-NfD deployment profile, Prometheus textfile
exporter, and 100% test coverage across every module.

### Added

- **VS-NfD deployment guide** — `docs/vsnfd-deployment.md`.
  Complete mapping of VSA requirements to Sentinel capabilities,
  deployment architecture, step-by-step instructions, and a
  20-item operator checklist. Closes #9.
- **`VSNfDReady` manifesto requirement** — checks the automatable
  subset of the VS-NfD profile: approved storage backend, German
  data residency, EU/LOCAL sovereign scope, kill switch presence,
  and policy evaluator configured. Explicitly documents what it
  does **not** check (physical security, personnel clearances).
- **Prometheus textfile exporter** — `sentinel.integrations.prometheus.PrometheusExporter`
  writes a `.prom` file readable by node-exporter's textfile
  collector. Metrics: sovereignty score, days to enforcement,
  kill switch state, decision counts per agent, latency p50/p95/p99,
  test coverage, manifesto score. Background thread with atomic
  file writes.
- **Docker compose integration** for Prometheus textfile metrics.
  Both `docker-compose.yml` and `docker-compose.minimal.yml` now
  mount a `sentinel-metrics` volume between the sentinel-demo
  container and a `node-exporter` container, so the Grafana
  dashboard panels show real data.
- **Optional extra** `pip install sentinel-kernel[prometheus]`.

### Changed

- **100% test coverage** across every module in `sentinel/`.
  421 tests passing (up from 344). Dev extras now pull every
  optional integration dep (langchain-core, opentelemetry-sdk,
  opentelemetry-exporter-otlp-proto-grpc, langfuse, psycopg2-binary,
  prometheus-client, rich) so the happy-path branches of every
  optional-dep import guard get exercised in CI.

### Fixed

- **`sentinel demo` default output path** — now uses
  `tempfile.gettempdir()` instead of the repo root, so repeated
  demo runs don't clutter the working tree.
- **`update-claude-md` CI race** — regenerate-reset-push loop
  (from v1.3.0) extended to cover the Python 3.11 terminal
  monkeypatch race that surfaced in #58.
- **Test terminal-width monkeypatch** now scopes its patch to the
  `sentinel.dashboard.terminal` module instead of replacing the
  global `shutil.get_terminal_size`, which used to crash pytest's
  own progress writer on the Python 3.11 CI runner.
- **Unused `statistics` import** and dead percentile branches
  removed from `sentinel.integrations.prometheus`.
- **Issue #2** (LangFuse integration) closed — delivered in v0.3.

## [1.5.0] — 2026-04-11

Minor release. Governance and community — Linux Foundation Europe
application preparation and a technical blog post draft.

### Added

- **LF Europe application preparation materials** at
  `docs/lf-europe-application/`. Prerequisites checklist, current
  status, application timeline, decision criteria, and an index
  of materials to be produced closer to the application date.
- **Technical blog post draft** —
  `docs/content/sovereign-ai-decision-infrastructure.md`. A
  ~1500-word CTO-level technical note on why AI decision
  infrastructure needs to be sovereign. Zero corporate filler,
  no hashtag recommendations. Peer-to-peer tone. Ready for review.

### Changed

- Governance docs (GOVERNANCE.md, CONTRIBUTING.md, SECURITY.md)
  reviewed for LF Europe submission readiness. No substantive
  changes required — the documents written in v1.3.0 already
  cover the prerequisites.

## [1.4.0] — 2026-04-11

Minor release. Integration depth — Haystack integration, integration
coverage ≥95%, and NDJSON trace export/import.

### Added

- **Haystack integration** — `sentinel.integrations.haystack.SentinelHaystackCallback`
  for deepset Haystack (Berlin, EU-sovereign). Component-level and
  pipeline-level tracing. Guarded with `ImportError`. Optional extra:
  `pip install sentinel-kernel[haystack]`. Closes #12.
- **Trace export/import** — `StorageBackend.export_ndjson()` and
  `import_ndjson()` on every backend. Filters: start/end, agent,
  project. Duplicate detection on import (skipped by `trace_id`).
  Enables sharing traces between environments, archiving to long-
  term storage, and loading sample data for demos.
- **`sentinel export` and `sentinel import` CLI commands**.

### Changed

- **PostgreSQL backend** — removed its specialised `export_ndjson`
  method in favour of the generic base-class implementation.
  Behaviour is identical; signature now supports filters.

### Coverage

- Integration coverage now: langchain 99%, langfuse 98%, otel 95%,
  haystack 100%. Total test suite: 344 passing, 96% overall.

## [1.3.0] — 2026-04-11

Minor release. Ecosystem and community — RFC-001 accepted,
CONTRIBUTING and SECURITY rewritten, richer industry examples.

### Added

- **RFC-001 ACCEPTED**. Open questions resolved, implementation
  reference document added at `docs/rfcs/RFC-001-implementation.md`.
  `tests/test_rfc001_compliance.py` validates a real manifesto
  against the spec.
- **CONTRIBUTING.md rewrite** — sovereignty posture statement
  template (mandatory on every PR), integration-add step-by-step
  guide including the five mandatory tests, jurisdiction database
  add guide, and security disclosure section.
- **SECURITY.md rewrite** — supported versions, 48-hour
  acknowledgement commitment, severity-based resolution timelines,
  scope (in/out), known limitations, cryptographic choices, CVE
  tracking placeholder.
- **examples/13_full_pipeline.py rewrite** — realistic document
  classifier + approval workflow. Wires classify → approve chain,
  kill-switch drill, scanners, manifesto, EU AI Act check, HTML
  report, and terminal summary. Runs in <2 seconds with zero
  optional extras.
- **examples/10_manifesto.py rewrite** — three industry scenarios
  side by side: defence (VS-NfD), healthcare (GDPR), enterprise
  (pragmatic with documented gaps).

### Fixed

- **`update-claude-md` CI job** — replaces rebase-and-retry with
  regenerate-reset-push loop. On non-fast-forward, resets hard to
  origin/main and re-runs the generator against the new HEAD,
  eliminating merge conflicts between concurrent auto-updates.

## [1.2.0] — 2026-04-11

Minor release. Depth across onboarding, governance, manifesto, and
sovereignty scanner.

### Added

- **Technical co-founder onboarding kit** — `docs/onboarding/technical-cofounder.md`.
  Covers architecture in five minutes, the three invariants, development
  setup, reading order, integration/storage extension guides, and
  release process.
- **Architecture Decision Records** — ADR-001 (local-first), ADR-002
  (Apache 2.0 permanent), ADR-003 (schema versioning). Structured
  records of the architectural commitments.
- **BSI IT-Grundschutz profile — expanded**. Complete Baustein mapping
  across APP.6, CON.1, CON.2, OPS.1.1.3, SYS.1.6, NET.1.2. Evidence
  index and automated-vs-operator split table. Ready for a real BSI
  pre-engagement conversation.
- **Manifesto — new requirement types**:
  - `GDPRCompliant` — checks EU data residency and hashed-input
    default.
  - `RetentionPolicy(max_days=N)` — declares operator-enforced
    retention.
  - `AuditTrailIntegrity` — verifies storage exposes no
    UPDATE/DELETE methods.
  - `BSIProfile(status, by, evidence)` — tracks BSI certification
    status and evidence path.
- **Scanner — expanded jurisdiction database**. 30+ new packages
  including CrewAI, AutoGen, Semantic Kernel, LlamaIndex, Haystack,
  Mistral AI, DeepL, Aleph Alpha, Scaleway, Hetzner, OVH, Groq,
  Perplexity, Pinecone, Weaviate, Qdrant, Chroma, Milvus.
- **Scanner — EU-sovereign alternatives map**.
  `RuntimeScanResult.sovereign_alternatives()` returns an
  `{us_package: suggestion}` map.
- **Scanner — `--suggest-alternatives` CLI flag**. Prints the
  EU-sovereign alternatives block alongside the scan. Works in
  both text and JSON output modes.
- **CI/CD scanner — Makefile, Jenkinsfile, Drone CI support**.
  Makefile scanner flags `curl`/`wget` calls to US cloud hosts
  (amazonaws.com, googleapis.com, azurewebsites.net, etc.).

### Fixed

- **CI race** — `update-claude-md` job now rebases and retries the
  self-push so concurrent commits during an auto-update don't cause
  non-fast-forward failures.
- **mypy** — `dict` → `dict[str, Any]` in `sentinel/cli.py`
  `_cmd_demo`.

## [1.1.0] — 2026-04-11

Minor release. Major visual overhaul of the public surface, new CLI
command for zero-setup demos, and production-grade Grafana dashboard.

### Added

- **World-class GitHub Pages preview** — complete redesign of
  `docs/preview/index.html` with a dark theme design system, hero
  section, animated terminal, enforcement banner, comparison table,
  6-panel live dashboard (all inline SVG), 3-tab code examples,
  industry scenarios, features list, and try-it block. Fully
  self-contained — zero external resources, safe for air-gapped hosts.
- **`sentinel demo` CLI command** — full end-to-end walkthrough with
  no Docker. Runs 50 realistic decisions, engages and disengages the
  kill switch, runs the sovereignty scanners, runs the EU AI Act
  checker, writes a self-contained HTML report, and prints a terminal
  summary. Exit 0 on success.
- **Docker minimal compose** — `demo/docker-compose.minimal.yml`
  starts a SQLite-backed sentinel + OTel + Prometheus + Grafana in
  under 60 seconds. No PostgreSQL, no LangFuse.
- **`demo/healthcheck.sh`** — verifies Grafana/Prometheus/OTel/LangFuse
  from the host.
- **Grafana dashboard 7-row redesign** — 18 panels covering sovereignty
  score, enforcement countdown, kill switch, live decision feed,
  policy distribution, latency p50/p95/p99, EU AI Act per-article
  coverage, human-action table, dependency map, operational status,
  and manifesto state.
- **OTel collector spanmetrics connector** — converts sentinel.decision
  spans into Prometheus metrics while preserving all sovereignty
  attributes as labels.

### Changed

- **HTML sovereignty report** — complete dark-theme redesign matching
  the preview. SVG gauge for sovereignty score, urgency-coloured
  enforcement countdown, priority-badged recommended actions,
  EU-vs-US row styling in dependency tables, "what to do" column in
  the EU AI Act table, executive summary for non-technical readers.
  Still fully self-contained.
- **Docker compose image pinning** — all images pinned to specific
  versions. Healthchecks on all services. `restart: unless-stopped`
  throughout. `depends_on: condition: service_healthy` for ordered
  startup.

### Fixed

- `NamedTemporaryFile` context-manager use in demo command (ruff SIM115).

## [1.0.1] — 2026-04-11

Patch release. No public API changes. Coverage hardened across the
integration layer and the storage backends, two missing reference
documents added, legacy examples removed, and duplicate issues
closed.

### Added

- `CLAUDE_MEGA_PROMPT.md` — persistent Claude Code reference at the
  repo root. Captures the real API, module map, CLI surface, release
  process, three sovereignty invariants, current version/test state,
  and roadmap. Update on every release so the next Claude Code
  session starts from a correct map.
- `docs/releasing.md` — release runbook. PyPI trusted-publisher setup
  (one-time), three-command flow, pre-tag checklist, SemVer rules for
  this codebase, and troubleshooting for every failure mode hit so
  far (invalid-publisher, 403 overwrite, wrong tag prefix, tag on
  wrong SHA, smoke-test ruff step).
- `tests/test_cli.py` — 25 tests covering every subcommand branch.
- `tests/test_storage_filesystem.py` — 29 tests covering every
  branch of the air-gap reference backend.

### Changed — coverage

- `sentinel/cli.py`: 70% → 97%. Defensive `_load_manifesto` now
  returns `None` on a missing file path instead of raising
  `FileNotFoundError`.
- `sentinel/storage/filesystem.py`: 78% → 100%.
- `sentinel/integrations/otel.py`: 73% → 95%. New tests cover the
  wrapper delegation (`initialise`, `get`), the policy-result span
  attribute when a policy evaluator is wired, `flush()`, the real
  `_import_otel()` ImportError path, and `_build_real_tracer()` via
  stubbed OTel classes.
- `sentinel/integrations/langchain.py`: 76% → 99%. New tests cover
  every branch of `_extract_model_name` and `_serialise_llm_result`,
  chain end with non-dict output, and the direct
  `_import_base_callback_handler` ImportError path.
- `sentinel/integrations/langfuse.py`: 78% → 98%. Covers the generic
  `update(trace_id=)` SDK shape, the `AttributeError` for unknown
  clients, the default-client path via `_import_langfuse_client()`,
  and the direct ImportError path.
- `sentinel/storage/postgres.py`: 84% → 99%. Covers the
  `policy_result` query filter, `get()` miss, `close()`, `__repr__`,
  `_coerce_payload` with JSON-string input, the direct
  `_import_psycopg2` ImportError path, and the default `connect_fn`
  path.
- Total tests: 275 → **304**. Overall coverage: 93% → **97%**.

### Changed — alignment with mega-prompt spec

- `sentinel/dashboard/terminal.py`: added public `TerminalReport`
  alias for `TerminalDashboard` and a `print_summary()` convenience
  wrapper around `render_once()`.
- `demo/grafana/`: reorganised to the canonical layout with
  `grafana/provisioning/{datasources,dashboards}/*.yaml` and
  `grafana/dashboards/sentinel_sovereignty.json`. Docker Compose
  mounts simplified to the two standard paths.
- `examples/policies/data_classification.rego` — UNCLASSIFIED → SECRET
  lattice with explicit deny reasons and three inline `opa test`
  cases.

### Removed — legacy duplication

- `examples/minimal_trace.py`, `examples/policy_deny.py`,
  `examples/quickstart.py`, `examples/manifesto_example.py` — all
  duplicated content already in the numbered 01-13 examples.
- `docs/quickstart.md` — consolidated into `docs/getting-started.md`.

### Fixed

- `docs/getting-started.md`: imported a non-existent `AirGapRequired`
  class. Switched to the real idiom (`Required()` with an attribute
  name starting with `airgap`). Also fixed the `AcknowledgedGap`
  constructor kwargs to match the real dataclass fields
  (`provider` / `migrating_to` / `by` / `reason`).
- `docs/rfcs/RFC-001-sovereignty-manifest.md`: the implementation-
  status section referenced the deleted
  `examples/manifesto_example.py`. Updated to `examples/10_manifesto.py`
  and refreshed the test count.
- `.github/workflows/ci.yml`: was still invoking the deleted
  `examples/minimal_trace.py` and `examples/policy_deny.py`. Switched
  to `examples/01_minimal_trace.py` and
  `examples/03_policy_simple_rule.py`.
- Duplicate issues #1 and #4 closed (superseded by #5 and #9).

## [1.0.0] — 2026-04-11

Stable release. The full v0.9.x feature set — kill switch, PostgreSQL
and filesystem storage, LangChain / OTel / LangFuse integrations,
air-gapped validation suite, sovereignty scanner, manifesto-as-code,
EU AI Act compliance checker, Docker Compose + Grafana demo, self-
contained HTML report, full CLI, 13 runnable examples, ecosystem
registry, and RFC-001 — promoted to `1.0.0` with test coverage
hardened around previously thin modules.

### Changed

- Marked as `Development Status :: 5 - Production/Stable`.
- `__version__` bumped to `1.0.0` in `sentinel/__init__.py` and
  `pyproject.toml`.

### Added — Coverage hardening

- `tests/test_policy_evaluator.py` — 14 new unit tests for
  `NullPolicyEvaluator`, `LocalRegoEvaluator`, and
  `SimpleRuleEvaluator`. Mocks `asyncio.create_subprocess_exec` so
  the Rego evaluator is exercised without requiring the OPA binary.
  `sentinel.policy.evaluator` coverage: 45% → 100%.
- `tests/test_manifesto_extra.py` — 22 new unit tests covering
  `Requirement.as_dict` serialisation for every requirement type,
  `Gap` / `MigrationPlan` / `DimensionStatus` to-dict conversion,
  `ManifestoReport.as_text` with and without gaps, the
  `OnPremiseOnly` / `Targeting` / unknown-requirement branches in
  `_check_requirement`, every branch of `_check_required_by_name`,
  and `_check_eu_ai_act_articles` with `sentinel=None`.
  `sentinel.manifesto.base` coverage: 73% → 100%.
- Total test count: 183 → 221. Overall coverage: 84% → 89%.

## [0.9.1] — 2026-04-11

Public-repo hardening and user-manual release. All v0.9.0 capabilities
are retained; this release focuses on making the project usable for
any developer in 5 minutes and removing any named-partner content
from the public repository.

### Changed

- **Public-repo compliance (P0).** Removed `demo/bwi/` and `demo/qs/`
  directories and all textual references to named partners from
  `README.md`, `CHANGELOG.md`, and `docs/ecosystem.md`. The public
  repository contains zero named partners, customers, or
  organisations. Industry scenarios in documentation are generic so
  any regulated organisation recognises their own situation.

### Added — User manual

- `docs/getting-started.md` — two-minute quickstart from
  `pip install` to first sovereign trace, policy, kill switch,
  compliance check, and manifesto.
- `docs/real-world-examples.md` — five generic industry scenarios
  (defence / aerospace, healthcare, financial services, public
  administration, enterprise procurement) each mapped to runnable
  examples and reference policies.

### Added — 13 runnable examples

Progressive complexity from minimal trace to full pipeline:

- `examples/01_minimal_trace.py` — 15-line first trace
- `examples/02_async_trace.py` — async function tracing
- `examples/03_policy_simple_rule.py` — SimpleRuleEvaluator ALLOW/DENY
- `examples/04_policy_rego.py` — LocalRegoEvaluator (graceful skip without OPA)
- `examples/05_kill_switch.py` — engage / block / disengage / resume
- `examples/06_filesystem_storage.py` — NDJSON air-gapped backend
- `examples/07_postgresql_storage.py` — PG backend (graceful skip without psycopg2)
- `examples/08_langchain_agent.py` — callback handler with a mocked LC
- `examples/09_otel_export.py` — OTel export with a fake tracer
- `examples/10_manifesto.py` — `SentinelManifesto` declaration and check
- `examples/11_compliance_report.py` — EU AI Act diff + HTML
- `examples/12_sovereignty_scan.py` — runtime / CI/CD / infra scan
- `examples/13_full_pipeline.py` — full stack end-to-end in one script

### Added — Policy templates

Five reference Rego policies covering common regulated domains:

- `examples/policies/procurement_approval.rego` — amount + requester-level
- `examples/policies/access_control.rego` — RBAC with audit-friendly denies
- `examples/policies/medical_escalation.rego` — risk-based escalation template
- `examples/policies/financial_transaction.rego` — amount / velocity / sanctions
- `examples/policies/mission_safety.rego` — autonomous-system go/no-go

### Added — Testing

- `tests/test_examples.py` — 17 tests that smoke-test every example
  via subprocess. Tests requiring external services (OPA binary,
  PostgreSQL) skip gracefully.
- `examples/smoke_test.py` expanded from 16 steps to **40 steps**.
  Now covers: scanner, manifesto, compliance checker, HTML report
  (self-contained check), example subprocess runs, sovereignty check,
  ruff clean, and full test suite. Exits 1 with a precise step and
  error message on any failure.

### Added — GitHub Pages preview

- `scripts/generate_preview.py` — builds a static preview page with
  inline SVG gauges / pie charts / bar charts using sample data.
  Zero external resource loads.
- `docs/preview/index.html` — landing page with live sample
  dashboard rendered from a 200-decision sample run.
- `docs/preview/report.html` — full self-contained HTML sovereignty
  report.
- `.github/workflows/pages.yml` — auto-deploys `docs/preview/` to
  GitHub Pages on every push to `main`.

### Notes

- `examples/smoke_test.py` is now the canonical release gate for
  this repository. A green smoke test means: every capability works,
  every example runs, the sovereignty check passes, lint is clean,
  and the full pytest suite is green.

## [0.9.0] — 2026-04-11

Status: Alpha → **Beta**.

The complete Sentinel sovereignty platform. v0.9 adds the evaluation,
declaration, and verification tooling on top of the v0.4 decision
kernel — aimed at any regulated organisation preparing for EU AI Act
Annex III enforcement.

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
- Documentation index extended with ecosystem registry and RFC-001.

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
