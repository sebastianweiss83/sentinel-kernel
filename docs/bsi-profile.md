# BSI IT-Grundschutz Profile

**Status:** Pre-engagement — formal BSI engagement planned alongside v2.0 (Q4 2026)
**Target:** BSI IT-Grundschutz reference profile for sovereign AI decision infrastructure
**Certification path:** IT-Grundschutz → VS-NfD deployment profile

This document maps Sentinel's architecture and controls to BSI
IT-Grundschutz Bausteine (building blocks) relevant to sovereign
AI middleware. It is intended as a pre-engagement conversation
starter and does not itself constitute a BSI assessment.

---

## Scope

The assessment scope covers:

- The `sentinel` Python package (kernel, storage, policy, dashboard,
  scanner, compliance modules).
- The reference deployment: SQLite or Filesystem storage, in-process
  policy evaluation, no network dependencies in the critical path.
- Optional integrations (`langchain`, `otel`, `langfuse`, `postgres`)
  are **out of scope** for the reference profile. Each integration
  documents its own sovereignty posture in the integration guide.

The assessment explicitly does **not** cover:

- The AI agents that Sentinel wraps — those are the customer's system.
- The LLM providers the AI agents call — those are separately governed.
- The underlying OS, container runtime, or hardware.

---

## Baustein mapping

### APP.6 — Allgemeine Software

APP.6 covers the acquisition, development, and operation of
application software.

| Requirement (summarised) | How Sentinel addresses it | Evidence | Operator action required |
|---|---|---|---|
| APP.6.A1 — Plan procurement / development | Open source Apache 2.0. Source fully available on GitHub. No licence negotiation required. | `LICENSE`, `README.md` | Document the version pinned and the SBOM in the operator's own records. |
| APP.6.A2 — Define security requirements | Three invariants (local-first, no CLOUD Act, air-gap). Enforced in every PR. | `CLAUDE.md`, `.claude/rules/sovereignty-rules.md` | Accept or refine these invariants for the deployment context. |
| APP.6.A3 — Secure software development | TDD workflow with 96%+ coverage. Linting, type checking, and air-gap tests in CI on every PR. | `.github/workflows/ci.yml`, `tests/test_airgap.py` | Require operator-side CI to pin Sentinel by hash. |
| APP.6.A4 — Input validation | Schema-validated trace inputs; SHA-256 hashing on by default. | `sentinel/core/trace.py` | Configure a `PolicyEvaluator` for domain-specific validation. |
| APP.6.A5 — Error handling | Errors logged and raised; trace-emission failures never silently swallowed. | `sentinel/core/tracer.py` | Wire logs to the operator's SIEM. |
| APP.6.A6 — Dependency management | Zero runtime dependencies in the core kernel. Optional extras gated by `ImportError`. | `pyproject.toml` | Mirror dependencies in an EU-sovereign PyPI mirror. |
| APP.6.A7 — Patch management | SemVer, public CHANGELOG, reproducible releases via OIDC trusted publisher. | `docs/releasing.md` | Subscribe to release notifications; pin by commit hash in air-gap deployments. |

---

### CON.1 — Kryptographie

CON.1 covers cryptographic methods and their secure implementation.

| Requirement | How Sentinel addresses it | Evidence | Operator action required |
|---|---|---|---|
| CON.1.A1 — Encryption at rest | SQLite and filesystem backends inherit OS-level encryption. PostgreSQL backend inherits server-side encryption. | `docs/architecture.md` | Enable LUKS / BitLocker / pg_crypto according to deployment class. |
| CON.1.A2 — Transport encryption | TLS mandatory for any remote backend (PostgreSQL over SSL, OTel via gRPC+TLS). The critical path has no network, so this applies only to optional exporters. | `sentinel/integrations/otel.py` | Provide the TLS termination and certificate management. |
| CON.1.A3 — Hash algorithms | SHA-256 for `inputs_hash` on every trace. No weak algorithms in the codebase. | `sentinel/core/trace.py` | None — algorithm choice is hardcoded. |
| CON.1.A4 — Key management | Sentinel does not generate, store, or transmit cryptographic keys. Key material is the operator's responsibility. | *n/a — see operator action* | Integrate with the operator's HSM / vault. Document in the operator's BSI profile. |

---

### CON.2 — Datenschutz (GDPR)

CON.2 maps BSI controls to GDPR data-protection requirements.

| Requirement | How Sentinel addresses it | Evidence | Operator action required |
|---|---|---|---|
| CON.2.A1 — Data minimisation | `inputs_hash` (SHA-256) replaces raw inputs by default. `inputs_raw` is opt-in per trace. | `sentinel/core/trace.py:DecisionTrace` | Review per-agent whether raw inputs are needed. Default is to say no. |
| CON.2.A2 — Purpose limitation | Traces are written only for the specified agent and policy. No cross-project sharing by default. | `sentinel/core/tracer.py:Sentinel.__init__` | Document the purpose of trace collection in the operator's DPIA. |
| CON.2.A3 — Data residency | `data_residency` field is asserted on every trace and is independently verifiable at the storage layer. | `sentinel/core/trace.py`, `sentinel/core/types.py:DataResidency` | Align `data_residency` with the actual storage location. |
| CON.2.A4 — Retention | Configurable per backend. Append-only storage means deletion is an operator-driven process, documented and audited. | `docs/bsi-profile.md` | Define retention period and archival process in the operator's records of processing. |
| CON.2.A5 — Data subject rights | Hash-based storage by default makes identifying an individual's traces impossible without the hashing salt. Raw-input traces are individually deletable via `StorageBackend.delete_trace`. | `sentinel/storage/base.py` | Operate a subject-access-request (SAR) workflow. |

---

### OPS.1.1.3 — Patch- und Änderungsmanagement

OPS.1.1.3 covers how software changes are tracked, approved, and
deployed.

| Requirement | How Sentinel addresses it | Evidence | Operator action required |
|---|---|---|---|
| OPS.1.1.3.A1 — Change process | PRs required for every change. Main branch is protected. RFC process for schema changes. | `docs/rfcs/`, GitHub branch protection rules | Mirror this discipline in the operator's own fork. |
| OPS.1.1.3.A2 — Release process | SemVer tags. OIDC trusted-publisher to PyPI. Reproducible builds. | `docs/releasing.md`, `.github/workflows/release.yml` | Pin by exact version or commit hash for classified deployments. |
| OPS.1.1.3.A3 — Changelog | CHANGELOG.md maintained for every release. Keep-a-Changelog format. | `CHANGELOG.md` | Include the changelog in operator-side change control. |
| OPS.1.1.3.A4 — Rollback capability | Every release is a separate sdist/wheel on PyPI. Rollback = pin to the previous version. Traces are append-only so no data is lost. | PyPI release history | Document operator rollback procedure. |
| OPS.1.1.3.A5 — Version pinning guidance | Air-gap deployments should pin by `--require-hashes` in `pip`. | `docs/bsi-profile.md` | Generate and check the hash-pinned requirements file. |

---

### SYS.1.6 — Containerisierung

SYS.1.6 applies when Sentinel is deployed inside containers. The
reference Docker deployment (`demo/`) is a convenience for
evaluation, not a production deployment.

| Requirement | How Sentinel addresses it | Evidence | Operator action required |
|---|---|---|---|
| SYS.1.6.A1 — Image provenance | All images in `demo/docker-compose.yml` are pinned to specific versions, not `:latest`. | `demo/docker-compose.yml` | Mirror images to an EU-sovereign registry (Harbor, GitLab). |
| SYS.1.6.A2 — Minimise attack surface | Minimal compose variant ships without PostgreSQL/LangFuse. | `demo/docker-compose.minimal.yml` | Run only services required by the deployment class. |
| SYS.1.6.A3 — Healthchecks | Every service has a liveness healthcheck. `depends_on: condition: service_healthy`. | `demo/docker-compose.yml` | Forward healthcheck state to the operator's monitoring. |
| SYS.1.6.A4 — Air-gapped container operation | The minimal compose works on a host with no internet access once images are local. | `demo/README.md` | Pre-pull images onto an offline host. |
| SYS.1.6.A5 — No phone-home | No Sentinel code makes unsolicited outbound connections. | `tests/test_airgap.py` | Run a network-sniffer test in the operator's own CI to verify. |

---

### NET.1.2 — Netzarchitektur

NET.1.2 covers how the system fits into a secured network zone.

| Requirement | How Sentinel addresses it | Evidence | Operator action required |
|---|---|---|---|
| NET.1.2.A1 — Network-free critical path | Sentinel operates with no network dependency. Traces are written to local storage synchronously. | `tests/test_airgap.py`, `sentinel/storage/sqlite.py` | Place Sentinel in the highest-trust zone. |
| NET.1.2.A2 — Optional exporters are additive | OTel and LangFuse export happens after local storage and cannot influence the critical path. | `sentinel/integrations/otel.py` | Configure egress firewall rules for the OTel collector endpoint only. |
| NET.1.2.A3 — Protocol neutrality | OTLP is an open CNCF standard. NDJSON export is human-readable. No proprietary protocols. | `docs/schema.md` | Point exporters at operator-hosted collectors on sovereign infrastructure. |
| NET.1.2.A4 — Air-gapped validation | CI runs the critical path with the network denied at the socket level. | `tests/test_airgap.py` | Re-run air-gap tests after any dependency change. |

---

## Evidence index — where to find it in the repository

| Area | File |
|---|---|
| Sovereignty invariants | `.claude/rules/sovereignty-rules.md` |
| Air-gap CI test | `tests/test_airgap.py` |
| Trace schema | `sentinel/core/trace.py`, `docs/schema.md` |
| Storage backends | `sentinel/storage/` |
| Runtime dependency scanner | `sentinel/scanner/runtime.py` |
| CI/CD dependency scanner | `sentinel/scanner/cicd.py` |
| EU AI Act compliance checker | `sentinel/compliance/euaiact.py` |
| Release runbook | `docs/releasing.md` |
| ADR — local-first | `docs/architecture-decision-records/ADR-001-local-first.md` |
| ADR — Apache 2.0 permanent | `docs/architecture-decision-records/ADR-002-apache2-permanent.md` |
| ADR — schema versioning | `docs/architecture-decision-records/ADR-003-schema-versioning.md` |

---

## Automated vs operator responsibility

Some controls Sentinel can enforce automatically. Others inherently
require the operator to act. This table summarises the split.

| Control area | Sentinel automates | Operator provides |
|---|---|---|
| Trace emission | Synchronous, append-only write to local storage. | Backup and retention. |
| Input validation | SHA-256 hashing, schema check, field presence. | Domain-specific policy rules. |
| Dependency sovereignty | CI scanner flags CLOUD Act–exposed packages. | Policy on which findings block a release. |
| Data residency | `data_residency` field on every trace. | Ensuring the physical storage matches the asserted residency. |
| Kill switch | `engage_kill_switch()` halts all agent calls. | Human oversight procedure around when to engage it. |
| Key management | None — by design. | HSM / vault integration. |
| Encryption at rest | None — inherited from OS/DB. | LUKS / BitLocker / pg_crypto configuration. |
| Risk management (Art. 9) | Automated policy evaluation results per trace. | Risk classification of the AI system itself. |
| Human oversight (Art. 14) | Kill switch + override chains. | Organisational process around who can engage them. |
| Logging (Art. 12) | Automatic, tamper-resistant, append-only. | Monitoring and alerting on log volume/absence. |

---

## VS-NfD prerequisites

VS-NfD (Verschlusssache — Nur für den Dienstgebrauch) is the lowest
German government classification level. Deployment of software in
VS-NfD environments requires additional controls beyond standard
IT-Grundschutz.

### Checklist

- [x] Air-gapped mode works end-to-end with no network connectivity
- [x] No mandatory internet connectivity in the critical path
- [x] All dependencies auditable and available offline
- [x] No telemetry, analytics, or phone-home behaviour
- [x] Trace storage works on local filesystem only
- [x] Policy evaluation is fully in-process (no remote policy service)
- [x] Network-isolated CI test suite
- [x] Export format (NDJSON) is human-readable and tool-independent
- [ ] Tested and validated in a real network-isolated environment
- [ ] Formal VS-NfD assessment (planned v2.0)

---

## Timeline

| Milestone | Target | BSI relevance |
|---|---|---|
| v1.0 — Production baseline | 2026-04 | Core trace emission and storage — baseline for assessment |
| v1.1 — Demo surface + dashboards | 2026-04 | Operator onboarding materials |
| v1.2 — Onboarding + BSI profile expansion | 2026-04 | This document; conversation-ready for pre-engagement |
| v1.4 — Haystack integration | 2026-Q2 | EU-sovereign agent framework coverage |
| v2.0 — BSI reference implementation | 2026-Q4 | Formal assessment against IT-Grundschutz |
| v2.1 — VS-NfD deployment profile | 2027-Q1 | Cleared for classified German government deployments |
