# Sovereign AI Ecosystem

A curated registry of projects that share Sentinel's sovereignty
principles. Every entry has been evaluated against the three
sovereignty tests:

1. **Jurisdiction** — is the parent entity or critical path under a
   non-EU jurisdiction with compelled-disclosure law?
2. **Air-gap capability** — can it run with zero external network?
3. **Certification path** — is there a plausible route to BSI /
   VS-NfD or comparable EU classification?

Inclusion is not an endorsement of every claim a project makes about
itself. It is a starting point for an informed evaluation.

---

## Decision record layer

### sentinel-kernel *(this project)*
- **Role:** EU-sovereign AI decision middleware kernel
- **Jurisdiction:** EU
- **Air-gap:** Yes — reference `FilesystemStorage` backend
- **Certification:** BSI IT-Grundschutz targeted for v1.0 (Q4 2026)

---

## Agent frameworks with a sovereignty posture

The picture here is honest: the popular frameworks (LangChain,
LangGraph, AutoGen, CrewAI, LlamaIndex) are all US-incorporated.
Sentinel works as a middleware layer on top of any of them — that is
why we wrap rather than replace. The integration does not make the
framework itself sovereign; it makes the *decision record* sovereign.

For EU-sovereign agent runtimes, investigate:

- **Haystack** (deepset, Berlin) — German-originated open-source NLP
  framework. Self-hostable, Apache 2.0.
- **KServe** + **PyTorch** (both Linux Foundation) — combine for
  model serving without a US vendor dependency.

Verify each project's current incorporation and runtime behaviour
before trusting any label — projects move.

---

## Observability (self-hostable)

### LangFuse — Berlin
- **Self-hosted on EU infra:** passes all three tests
- **LangFuse Cloud:** shared infrastructure — evaluate carefully
- **Integration:** `sentinel.integrations.langfuse.LangFuseEnricher`
  attaches Sentinel sovereignty metadata to LangFuse traces via the
  shared `trace_id` join key.

### Grafana + Prometheus + OpenTelemetry Collector
- **Jurisdiction:** Grafana Labs (UK), CNCF (neutral)
- **Self-hostable on EU infra:** passes all three tests
- **Integration:** `sentinel.integrations.otel.OTelExporter` emits
  `sentinel.decision` spans with full sovereignty metadata.

---

## Storage backends for sovereign deployment

| Backend          | Jurisdiction  | Sentinel support         | Notes |
|------------------|---------------|--------------------------|-------|
| SQLite           | Public domain | `SQLiteStorage`          | Default. Single-node. |
| PostgreSQL       | Neutral (PGDG)| `PostgresStorage` (extra)| v0.2 and above. |
| Filesystem NDJSON| N/A           | `FilesystemStorage`      | Reference air-gapped backend. |

---

## Infrastructure

Mature EU-sovereign cloud providers with Terraform support:

- **STACKIT** (Schwarz Group, DE) — EU-sovereign cloud with IONOS peering
- **IONOS Cloud** (DE)
- **Hetzner Cloud** (DE)
- **Scaleway** (FR)
- **OVHcloud** (FR)

For classified / VS-NfD work:

- **BWI Betrieb** (DE, federally owned) — sovereign infrastructure for
  German federal and defence customers.

None of these are endorsed by Sentinel — they are starting points for
a procurement evaluation. Run `sentinel scan` against your actual
Terraform to see what you have today.

---

## Coming

- **RFC-001** — `SovereigntyManifest` specification. A machine-readable
  standard for expressing and verifying sovereignty requirements,
  designed to be portable beyond Sentinel. See
  [docs/rfcs/RFC-001-sovereignty-manifest.md](rfcs/RFC-001-sovereignty-manifest.md).
- **BSI profile** — v1.0 target. See
  [docs/bsi-profile.md](bsi-profile.md).

---

## Contributing to the registry

Open a PR editing this file with:

1. Project name and link
2. Jurisdiction of parent entity
3. Evidence the project can run air-gapped
4. Evidence of a certification path (if claimed)
5. One-line description of the role it plays

We will not accept entries whose sovereignty claims cannot be
independently verified.
