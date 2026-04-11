# ADR-003: Schema Versioning for DecisionTrace

## Status
Accepted

## Context

The `DecisionTrace` schema must be stable enough for regulatory
compliance. Organisations store traces as evidence for audits that
may happen years after the trace was recorded. A trace recorded in
2026 must still be readable in 2030 — by both Sentinel and by any
third-party tool that speaks the trace format.

At the same time, the project is young and we expect to learn which
fields actually matter. We need a way to evolve the schema without
breaking old traces.

## Decision

Every `DecisionTrace` carries a `schema_version` field. The schema
itself is versioned with the library using SemVer.

**Rules:**

- **Adding optional fields** — no version bump required. Old readers
  see unknown fields and ignore them.
- **Adding mandatory fields** — requires an RFC (`/project:rfc`), a
  14-day comment period, and a minor version bump. The new field
  must have a sensible default that can be backfilled onto old
  traces.
- **Renaming or removing fields** — requires an RFC, a 14-day comment
  period, and a **major** version bump.
- **Changing field semantics** without a rename — forbidden. If
  semantics change, the field must be renamed.

The `schema_version` is embedded in every trace, not just in library
documentation. Any tool can read a trace, see `schema_version`, and
look up the exact schema at that version.

## Consequences

### Positive

- Regulatory auditors can reconstruct historical system state from
  any trace file, regardless of how far the library has evolved.
- Breaking changes are rare and deliberate — they require RFC
  consensus, not a solo decision.
- Third-party implementations (e.g. a Rust port of the SovereigntyManifest
  from RFC-001) can target specific schema versions.
- Old traces are always parseable by newer versions of Sentinel.

### Negative

- Every schema discussion becomes an RFC. This is intentional
  friction — the schema is the contract.
- Deprecated fields linger longer than they might in a fast-moving
  library.

## Alternatives considered

- **Implicit versioning from library version** — rejected. Couples
  schema lifetime to library lifetime, which breaks third-party
  implementations.
- **JSON Schema with per-field deprecation** — deferred. Worth
  revisiting once we have at least two breaking changes to learn from.
