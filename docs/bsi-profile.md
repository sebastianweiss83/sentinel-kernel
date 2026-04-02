# BSI IT-Grundschutz Profile

**Status:** Pre-engagement — formal BSI engagement planned alongside v1.0 (Q4 2026)
**Target:** BSI IT-Grundschutz compliance for sovereign AI decision infrastructure
**Certification path:** IT-Grundschutz → VS-NfD deployment profile

This document maps Sentinel's architecture and controls to BSI IT-Grundschutz
bausteine (building blocks) relevant to sovereign AI middleware.

---

## Baustein mapping

### APP.6 — Software (Individualsoftware)

| Requirement | Sentinel status | Notes |
|---|---|---|
| APP.6.A1 — Security requirements | Documented in CLAUDE.md and sovereignty rules | Three invariants enforced in all contributions |
| APP.6.A2 — Input validation | All public interfaces validate inputs | Schema validation on trace fields |
| APP.6.A3 — No hardcoded credentials | Enforced by code review and CI | No secrets in code, traces, or logs |
| APP.6.A4 — Error handling | Errors never leak internal state | Trace emission failures are logged, not swallowed |
| APP.6.A5 — Dependency management | All dependencies pinned to exact versions | Zero mandatory dependencies in core kernel |

### CON.1 — Cryptography

| Requirement | Sentinel status | Notes |
|---|---|---|
| CON.1.A1 — Encryption at rest | Storage backends support encryption at rest | Implementation-specific (filesystem: OS-level, DB: native encryption) |
| CON.1.A2 — Transport encryption | TLS required for any network transport | Air-gapped mode has no network transport |
| CON.1.A3 — Hash algorithms | SHA-256 for input hashing | No weak algorithms (MD5, SHA-1) permitted |
| CON.1.A4 — Key management | *Placeholder — to be documented before formal engagement* | Key management strategy depends on deployment context |

### CON.3 — Data protection (Datenschutz)

| Requirement | Sentinel status | Notes |
|---|---|---|
| CON.3.A1 — No raw PII by default | `inputs_hash` replaces raw inputs; `inputs_raw` is opt-in only | Data minimisation by design |
| CON.3.A2 — Data residency | Asserted in every trace via `data_residency` field | Independently verifiable |
| CON.3.A3 — Deletion path | Documented for each storage backend | Append-only for audit; archival deletion with documented process |

### OPS.1.1.5 — Data backup (Datensicherung)

| Requirement | Sentinel status | Notes |
|---|---|---|
| OPS.1.1.5.A1 — Backup capability | Traces exportable as NDJSON | Standard format, no proprietary tooling required |
| OPS.1.1.5.A2 — Restore capability | NDJSON import supported | Restore to any compatible storage backend |
| OPS.1.1.5.A3 — Air-gapped export | Works with no network | Reference deployment for classified environments |

---

## VS-NfD prerequisites

VS-NfD (Verschlusssache — Nur für den Dienstgebrauch) is the lowest German
government classification level. Deployment of software in VS-NfD environments
requires additional controls beyond standard IT-Grundschutz.

### Checklist

- [ ] Air-gapped mode works end-to-end with no network connectivity
- [ ] No mandatory internet connectivity in the critical path
- [ ] All dependencies auditable and available offline
- [ ] No telemetry, analytics, or phone-home behaviour
- [ ] Trace storage works on local filesystem only
- [ ] Policy evaluation is fully in-process (no remote policy service)
- [ ] Tested and validated in a network-isolated environment
- [ ] Export format (NDJSON) is human-readable and tool-independent
- [ ] No US CLOUD Act exposure in any component of the deployment

### Status

- Air-gapped filesystem storage: **Implemented** (v0.1)
- In-process policy evaluation: **Implemented** (v0.1)
- Network-isolated test suite: **Planned** (v0.4)
- Formal VS-NfD assessment: **Planned** (v1.1, Q1 2027)

---

## Key management

*This section will be completed before formal BSI engagement.*

Key management requirements depend on the deployment context:

- **Air-gapped / classified:** Key material managed by the deploying organisation.
  Sentinel does not generate, store, or transmit cryptographic keys.
- **On-premise enterprise:** Integration with existing key management
  infrastructure (e.g. HSM, vault) via the storage backend.
- **Development:** No encryption at rest required for local development.

---

## Timeline

| Milestone | Target | BSI relevance |
|---|---|---|
| v0.1 — Kernel | Q2 2026 | Core trace emission and storage — baseline for assessment |
| v0.4 — Air-gapped validation | Q3 2026 | Network-isolated test suite — prerequisite for VS-NfD |
| v1.0 — BSI reference implementation | Q4 2026 | Formal assessment against IT-Grundschutz |
| v1.1 — VS-NfD deployment profile | Q1 2027 | Cleared for classified German government deployments |
