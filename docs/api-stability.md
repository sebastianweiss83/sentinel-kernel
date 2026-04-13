# API Stability Guarantees

Sentinel 3.0 freezes the public API for the 3.x line. This
document names every public API and classifies it as **STABLE**,
**BETA**, or **EXPERIMENTAL**.

## 3.x stability commitments

Everything listed as STABLE below will not break without a major
version bump and a minimum six-month deprecation notice:

- `Sentinel` class — all public methods and signatures
- `DecisionTrace` dataclass — all fields (new optional fields may
  be added; existing fields remain)
- `StorageBackend` ABC — all abstract methods
- `PolicyEvaluator` ABC — all abstract methods
- `SentinelManifesto` base class and all requirement classes
- `EUAIActChecker.check()` and the `ComplianceReport` structure
- All CLI commands: `sentinel scan/compliance/report/demo/
  attestation/keygen/manifesto/verify/purge/export/import/
  ci-check/evidence-pack`
- All integration class names and constructor signatures
- `trace_id` format (UUIDv4 string)
- NDJSON export format
- `schema_version` field (currently `"1.0.0"`)
- Attestation schema version (currently `"1.0.0"`)

**Experimental in 3.x** (may change without notice):

- `QuantumSafeSigner` — pending stability of upstream liboqs-python
- Rust `sentinel-manifest` — pre-1.0, API may change
- `BudgetTracker` — new in 2.1, gathering feedback

## Definitions

| Label | Meaning |
|---|---|
| **STABLE** | Guaranteed no breaking changes in 2.x. New fields may be added. Existing fields, methods, and call signatures are frozen. |
| **BETA** | May change with a deprecation notice — at least one minor release warning before any breaking change. |
| **EXPERIMENTAL** | May change without notice. Use at your own risk in production. Document the specific revision in your dependencies. |

Breaking changes to STABLE APIs require a major version bump (3.0).

## Classification

### Core decision layer — **STABLE**

| API | Status | Since |
|---|---|---|
| `sentinel.Sentinel` | STABLE | 1.0 |
| `Sentinel.__init__(storage, project, data_residency, sovereign_scope, policy_evaluator, store_inputs, store_outputs)` | STABLE | 1.0 |
| `@sentinel.trace` decorator | STABLE | 1.0 |
| `Sentinel.engage_kill_switch(reason)` | STABLE | 1.0 |
| `Sentinel.disengage_kill_switch(reason)` | STABLE | 1.0 |
| `Sentinel.kill_switch_active` property | STABLE | 1.0 |
| `Sentinel.query(project, agent, policy_result, limit, offset)` | STABLE | 1.0 |
| `Sentinel.verify_integrity(trace_id)` | STABLE | 1.7 |
| `DecisionTrace` (all mandatory fields) | STABLE | 1.0 |
| `DecisionTrace.to_dict()` / `from_dict()` | STABLE | 1.0 |
| `DecisionTrace.to_json()` | STABLE | 1.0 |
| `DataResidency` enum | STABLE | 1.0 |
| `PolicyResult` enum | STABLE | 1.0 |
| `PolicyEvaluation` | STABLE | 1.0 |
| `HumanOverride` | STABLE | 1.0 |
| `PolicyDeniedError`, `KillSwitchEngaged` | STABLE | 1.0 |
| `IntegrityResult` | STABLE | 1.7 |

### Storage — **STABLE** interface, **STABLE** reference backends

| API | Status | Since |
|---|---|---|
| `StorageBackend` abstract base | STABLE | 1.0 |
| `StorageBackend.initialise()` | STABLE | 1.0 |
| `StorageBackend.save(trace)` | STABLE | 1.0 |
| `StorageBackend.query(...)` | STABLE | 1.0 |
| `StorageBackend.get(trace_id)` | STABLE | 1.0 |
| `StorageBackend.export_ndjson(...)` | STABLE | 1.4 |
| `StorageBackend.import_ndjson(...)` | STABLE | 1.4 |
| `StorageBackend.purge_before(cutoff, dry_run)` | STABLE | 1.7 |
| `SQLiteStorage` | STABLE | 1.0 |
| `FilesystemStorage` | STABLE | 1.0 |
| `PostgresStorage` | STABLE | 1.0 |
| `PurgeResult` | STABLE | 1.7 |

### Manifesto — **STABLE**

| API | Status | Since |
|---|---|---|
| `SentinelManifesto` | STABLE | 1.0 |
| `EUOnly`, `ZeroExposure`, `OnPremiseOnly`, `Required`, `Targeting`, `AcknowledgedGap` | STABLE | 1.0 |
| `GDPRCompliant`, `RetentionPolicy`, `AuditTrailIntegrity`, `BSIProfile` | STABLE | 1.2 |
| `VSNfDReady` | STABLE | 1.6 |
| `ManifestoReport`, `DimensionStatus`, `Gap`, `MigrationPlan` | STABLE | 1.0 |

### Compliance — **STABLE**

| API | Status | Since |
|---|---|---|
| `EUAIActChecker`, `ComplianceReport`, `ArticleReport`, `HumanActionItem` | STABLE | 1.0 |
| `DoraChecker`, `DoraReport` | STABLE | 1.9 |
| `NIS2Checker`, `NIS2Report` | STABLE | 1.9 |
| `UnifiedComplianceChecker`, `UnifiedReport` | STABLE | 1.9 |

### Scanner — **STABLE**

| API | Status | Since |
|---|---|---|
| `RuntimeScanner`, `ScanResult`, `PackageReport` | STABLE | 1.0 |
| `CICDScanner`, `CICDScanResult`, `CICDFinding` | STABLE | 1.0 |
| `InfrastructureScanner`, `InfraScanResult`, `InfraFinding` | STABLE | 1.0 |
| `RuntimeScanner.sovereign_alternatives()` | STABLE | 1.2 |
| `sentinel.scanner.knowledge.PACKAGE_KNOWLEDGE` | BETA — data, not API. New entries are additive. |
| `sentinel.scanner.knowledge.EU_ALTERNATIVES` | BETA — same as above. |

### Dashboard — **STABLE**

| API | Status | Since |
|---|---|---|
| `HTMLReport` | STABLE | 1.0 |
| `TerminalDashboard` / `TerminalReport` alias | STABLE | 1.0 |

### Integrations — **STABLE** where marked

| Integration | Status | Since |
|---|---|---|
| `sentinel.integrations.langchain.SentinelCallbackHandler` | STABLE | 1.0 |
| `sentinel.integrations.haystack.SentinelHaystackCallback` | STABLE | 1.4 |
| `sentinel.integrations.otel.OTelExporter` | STABLE | 1.0 |
| `sentinel.integrations.langfuse.LangFuseEnricher` | STABLE | 1.0 |
| `sentinel.integrations.prometheus.PrometheusExporter` | STABLE | 1.6 |
| `sentinel.integrations.jupyter.SentinelWidget` | BETA | 1.8 — notebook widget API may gain display-mode tweaks |
| `sentinel.integrations.fastapi.SentinelMiddleware` | STABLE | 1.8 |
| `sentinel.integrations.django.SentinelMiddleware` | STABLE | 1.8 |

### Policy evaluators — **STABLE**

| API | Status | Since |
|---|---|---|
| `PolicyEvaluator` abstract | STABLE | 1.0 |
| `NullPolicyEvaluator` | STABLE | 1.0 |
| `SimpleRuleEvaluator` | STABLE | 1.0 |
| `LocalRegoEvaluator` | BETA | 1.0 — OPA integration may gain performance hooks |
| `PolicyVersion` | BETA | 1.7 — experimental; field set may expand |

### CLI — **STABLE**

The `sentinel` console script is STABLE for subcommand names, flag
names, and exit codes. New subcommands and flags are additive.

| Subcommand | Status | Since |
|---|---|---|
| `sentinel demo` | STABLE | 1.1 |
| `sentinel scan` | STABLE | 1.0 |
| `sentinel compliance check` | STABLE | 1.0 |
| `sentinel report` | STABLE | 1.0 |
| `sentinel dashboard` | STABLE | 1.0 |
| `sentinel manifesto check` | STABLE | 1.0 |
| `sentinel export`, `sentinel import` | STABLE | 1.4 |
| `sentinel verify` | STABLE | 1.7 |
| `sentinel purge` | STABLE | 1.7 |
| `sentinel dora check`, `sentinel nis2 check` | STABLE | 1.9 |

### Schema

The `DecisionTrace` JSON schema is **STABLE** at `schema_version = 1.0.0`.
Schema changes follow ADR-003: optional fields can be added without
a version bump; renames or removals require a major version bump
and a 14-day RFC period.

## Deprecation policy

- A deprecation warning is logged for at least one minor release
  before a BETA API becomes STABLE or changes shape.
- STABLE APIs are not removed or reshaped without a major version
  bump.
- The CHANGELOG.md entry for every release names any deprecation
  introduced.

## Pinning for classified deployments

For VS-NfD or BSI-assessed deployments, pin by exact version **and**
hash:

```
sentinel-kernel==2.0.0 --hash=sha256:...
```

This is the operator's responsibility; see `docs/vsnfd-deployment.md`.
