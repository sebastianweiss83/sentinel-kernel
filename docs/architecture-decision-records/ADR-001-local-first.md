# ADR-001: Local storage is the reference deployment

## Status
Accepted

## Context

Sentinel's job is to record AI decision traces as legally defensible
evidence. There are three broad architectural options:

1. **Cloud-first** — write to a hosted observability backend by default
   (Datadog, Honeycomb, LangFuse Cloud, etc.). Local storage is a
   fallback.
2. **Dual-write** — write to local storage and a cloud backend in
   parallel, with neither being "primary".
3. **Local-first** — write to local storage in the critical path, with
   cloud/OTel exports as additive, out-of-critical-path enrichment.

We are building for regulated EU industries where:

- Air-gapped classified deployments are a valid target context.
- The US CLOUD Act creates a structural conflict with sovereignty
  guarantees for any US-incorporated backend.
- EU AI Act Art. 12 mandates durable logging — a dropped trace caused
  by a network failure is a compliance incident.
- The BSI certification path requires verifiable data residency.

## Decision

**Local storage is the reference deployment.** Every Sentinel feature
must work with `SQLiteStorage` or `FilesystemStorage` alone. Cloud
exporters (OTel, LangFuse) run after the local write has succeeded and
cannot influence the critical path.

Concretely:

- `Sentinel.storage.save(trace)` runs synchronously and durably.
- OTel/LangFuse wrappers decorate the storage layer from the outside;
  their failures are logged and swallowed.
- The air-gap test suite (`tests/test_airgap.py`) runs the entire
  critical path with the network denied at the socket level.
- `docker-compose.minimal.yml` demonstrates the full stack with SQLite
  and no PostgreSQL dependency.

## Consequences

### Positive

- Sovereignty is structurally enforced. No network, no problem.
- Air-gapped environments are a first-class target, not a degraded mode.
- Regulated customers can verify residency by looking at the filesystem.
- OTel/LangFuse are optional extras — zero cost to users who skip them.

### Negative

- Multi-node distributed decisions require the operator to wire their
  own replication (PostgreSQL with streaming replication, filesystem
  rsync, etc.). Sentinel does not provide this.
- "Single source of truth" lives locally, which means operators must
  run backups. We document this in `docs/bsi-profile.md`.

## Alternatives considered

- **Cloud-first** — rejected. Any US-owned cloud creates CLOUD Act
  exposure. An EU-based cloud still introduces a network dependency
  in the critical path, which breaks the air-gap invariant.
- **Dual-write** — rejected. Defining "which write is authoritative"
  creates ambiguity. Regulators need a single, unambiguous record.
