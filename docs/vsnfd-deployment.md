# VS-NfD Deployment Guide

_Verschlusssache — Nur für den Dienstgebrauch._
_The minimum classification level for restricted German government information._

## What VS-NfD means

VS-NfD is the lowest German classification level, defined in the
_Verschlusssachenanweisung_ (VSA). It applies to information whose
disclosure could harm public interests. Most German government AI
deployments that touch citizen data, law enforcement decisions, or
procurement workflows fall under VS-NfD.

This guide describes how to deploy `sentinel-kernel` in a VS-NfD
environment. It does **not** authorise such a deployment — that is
the responsibility of the operator's BSI-recognised security officer.
This document is technical guidance only.

## Requirements Sentinel must meet for VS-NfD

| # | Requirement | Source |
|---|---|---|
| 1 | Data residency: Federal Republic of Germany only | BSI IT-Grundschutz + operator contracts |
| 2 | No foreign jurisdiction access: zero US CLOUD Act exposure | CLOUD Act risk analysis (BSI position paper 2022) |
| 3 | Air-gapped operation: no mandatory external connections | BSI IT-Grundschutz SYS.1.6.A4 |
| 4 | Audit trail: tamper-resistant, append-only, durable | EU AI Act Art. 12, BSI OPS.1.1.3 |
| 5 | Access control: role-based, logged | BSI ORP.4 |
| 6 | Encryption: at rest and in transit | BSI CON.1 |
| 7 | Classified information handling: marking, segregation | VSA §2–§6 |

## How Sentinel satisfies each requirement

### 1. Data residency — Federal Republic of Germany only

- `DataResidency.EU_DE` on every trace is the machine-readable
  assertion.
- Storage backends: `SQLiteStorage`, `FilesystemStorage`, or
  `PostgresStorage` — all local-file or on-premise database.
- Operator action: ensure the physical storage is located in DE
  and document in the operator's VSA records.

Evidence: `sentinel/core/trace.py:DecisionTrace`, field
`data_residency`.

### 2. Zero US CLOUD Act exposure

- Critical path has no US-incorporated runtime dependencies.
- Verified by CI (`scripts/check_sovereignty.py`).
- Runtime scanner enumerates every installed package and flags any
  CLOUD Act exposure.

Evidence: `sentinel/scanner/runtime.py`, `tests/test_scanner.py`,
CI sovereignty job in `.github/workflows/ci.yml`.

### 3. Air-gapped operation

- Sentinel's critical path works with the network denied at the
  socket level.
- 11 dedicated air-gap tests in `tests/test_airgap.py`.
- Optional exporters (OTel, LangFuse) run _after_ the local write
  and never gate the critical path.

Evidence: `tests/test_airgap.py` — must pass on every PR.
Operator action: deploy into a network segment with no external
egress.

### 4. Tamper-resistant audit trail

- All storage backends are append-only (`StorageBackend` base class
  exposes no UPDATE or DELETE on traces).
- SHA-256 hashing on every input by default.
- Schema versioned — old traces remain readable by newer versions.

Evidence: `sentinel/storage/base.py`, `AuditTrailIntegrity`
manifesto requirement (v1.2+).

### 5. Access control

- Sentinel itself does not implement user access control — it runs
  inside the operator's process.
- The operator provides access control at the storage layer
  (PostgreSQL roles, filesystem permissions) and the orchestration
  layer (mTLS, Kerberos, RBAC).

Operator action: define roles, map to storage ACLs, enable the
SIEM connector of choice.

### 6. Encryption

- **At rest:** inherit from the filesystem (LUKS) or database
  (pg_crypto / TDE). Sentinel does not implement its own
  at-rest encryption.
- **In transit:** TLS is mandatory for any remote backend. The
  critical path has no network, so this only applies to optional
  exporters.

Operator action: provision LUKS volumes or TDE-enabled PostgreSQL.
Document key management in the VSA records.

### 7. Classified information marking

- `sovereign_scope` and `data_residency` on every trace are the
  machine-readable equivalents of VSA markings.
- Tags (`trace.tags`) can carry additional classification metadata
  — e.g. `tags={"vsnfd": "true", "classification_basis": "VSA §5"}`.

## Deployment architecture (ASCII)

```
                     ┌──────────────────────────────────┐
                     │    AIR-GAPPED NETWORK SEGMENT     │
                     │      (BSI zone N2 or higher)      │
                     │                                    │
  ┌────────────┐     │   ┌───────────────────────────┐   │
  │  AI agent  │────▶│   │  sentinel kernel           │   │
  │  (any      │     │   │  (@sentinel.trace)         │   │
  │   model)   │     │   └─────────┬─────────────────┘   │
  └────────────┘     │             │ synchronous write    │
                     │             ▼                       │
                     │   ┌───────────────────────────┐    │
                     │   │  PostgreSQL               │    │
                     │   │  (pg_crypto, LUKS disk)   │    │
                     │   │  append-only              │    │
                     │   └───────────┬───────────────┘    │
                     │               │                     │
                     │               ▼                     │
                     │   ┌───────────────────────────┐    │
                     │   │  self-hosted Grafana      │    │
                     │   │  (read-only, same segment)│    │
                     │   └───────────────────────────┘    │
                     │                                    │
                     └──────────────────────────────────┘
                     no external connections required
```

## Step-by-step deployment

### Step 1 — install in an isolated environment

```bash
# On the connected build host, produce a wheel + vendored deps
pip download sentinel-kernel -d offline-packages/
pip wheel sentinel-kernel -w offline-packages/

# Transfer offline-packages/ via approved transfer media
# On the classified host:
pip install --no-index --find-links /media/offline-packages/ sentinel-kernel
```

### Step 2 — configure sovereign storage

```python
from sentinel import Sentinel, DataResidency
from sentinel.storage.postgres import PostgresStorage

sentinel = Sentinel(
    storage=PostgresStorage(
        "postgresql://sentinel:***@localhost/sentinel_traces",
        min_connections=2,
        max_connections=20,
    ),
    project="classified-deployment-01",
    data_residency=DataResidency.EU_DE,
    sovereign_scope="EU",
)
```

### Step 3 — declare the VS-NfD manifesto

```python
from sentinel.manifesto import (
    SentinelManifesto,
    EUOnly,
    Required,
    OnPremiseOnly,
    ZeroExposure,
    AuditTrailIntegrity,
    BSIProfile,
    VSNfDReady,  # v1.6.0+
)


class VSNfDManifesto(SentinelManifesto):
    jurisdiction = EUOnly()
    cloud_act    = ZeroExposure()
    storage      = OnPremiseOnly(country="DE")
    kill_switch  = Required()
    airgap       = Required()
    audit        = AuditTrailIntegrity()
    vsnfd        = VSNfDReady()
    bsi          = BSIProfile(
        status="pursuing",
        by="2026-Q4",
        evidence="docs/bsi-profile.md",
    )


report = VSNfDManifesto().check(sentinel=sentinel)
assert report.overall_score == 1.0, report.as_text()
```

### Step 4 — verify the air-gap

```bash
pytest tests/test_airgap.py -v
# All air-gap tests must pass. A single failure is a deployment
# blocker, not a warning.
```

### Step 5 — generate the compliance report

```bash
sentinel compliance check --html > vsnfd_compliance.html
sentinel report --output sovereignty_report.html --manifesto \
    path/to/policies.py:VSNfDManifesto
```

Keep both files in the operator's VSA records alongside the
deployment log.

## What Sentinel does NOT cover

- **Physical security** of the deployment environment.
- **Network segmentation** (operator responsibility — VSA §5).
- **Personnel security clearance** (SÜ1 / SÜ2 / SÜ3).
- **Hardware Security Module (HSM)** for key management.
- **PKI / certificate management.**
- **VSA marking of the physical media.**

These are out of scope for a software kernel and are the
operator's responsibility.

## Checklist for VS-NfD deployment

- [ ] Deployment environment is in a BSI zone N2 or higher network segment
- [ ] No external egress from the segment (verified with a sniffer)
- [ ] Physical storage is located in the Federal Republic of Germany
- [ ] LUKS or TDE at rest, documented in VSA records
- [ ] TLS on any intra-segment network hop (even though none are mandatory)
- [ ] PostgreSQL storage backend chosen — not SQLite (not suitable for multi-user classified)
- [ ] `data_residency=DataResidency.EU_DE` on every `Sentinel` instance
- [ ] `sovereign_scope="EU"` on every `Sentinel` instance
- [ ] `VSNfDManifesto` check returns `overall_score == 1.0`
- [ ] `pytest tests/test_airgap.py` passes on the deployment host
- [ ] `python scripts/check_sovereignty.py` passes on the deployment host
- [ ] Sovereignty scanner has been run and its output is in the VSA records
- [ ] EU AI Act compliance report has been generated and archived
- [ ] Kill switch has been tested end-to-end (`engage_kill_switch("test")`)
- [ ] Operator has defined who can engage the kill switch (VSA §6 roles)
- [ ] Backup and restore has been tested with `export_ndjson` / `import_ndjson`
- [ ] Personnel involved hold the appropriate Sicherheitsüberprüfung
- [ ] A BSI-recognised security officer has signed off on the deployment
- [ ] The operator has a documented incident response playbook
- [ ] Retention period is set and documented per operator's VSA records
- [ ] CLAUDE.md-equivalent operator documentation exists for the deployment
- [ ] Quarterly sovereignty scan is scheduled

## Further reading

- `docs/bsi-profile.md` — full BSI IT-Grundschutz mapping
- `docs/rfcs/RFC-001-sovereignty-manifest.md` — manifesto spec
- `docs/architecture-decision-records/` — architectural commitments
- BSI _Verschlusssachenanweisung_ (public sections)
- _BSI position paper on CLOUD Act_ (2022, public)
