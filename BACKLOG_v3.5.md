# Sentinel v3.5 Architecture Backlog

This document captures the four architectural directions identified
for v3.5 based on early enterprise architect feedback. These are
open architectural questions, not committed implementations. Module
structure, naming, and design will be decided in collaboration with
design partners.

## Item 1: Causal context across decisions

The need: when agents trigger other agents, evidence must preserve
the causal relationships, not just the temporal sequence. Hash-chain
(v3.4) gives us temporal linkage. Causal linkage requires reading
parent-child trace context from upstream observability layers when
present.

Open architectural questions:

- Read OpenTelemetry context when present, or define our own causal
  model?
- If OTEL: which semantic conventions, which versions, which
  extension points?
- How does causal context interact with the existing
  `ChainNamespace` concept?
- Should this be a core capability or a bridge module to adjacent
  observability stacks?

No code committed. Design partner input pending.

## Item 2: Long-term semantic interpretability

The need: in 10-15 year retention scenarios, attestations stored as
opaque JSON become uninterpretable when the original team and tooling
are gone. Self-describing semantic formats (RDF, JSON-LD, alignment
with W3C provenance ontologies) preserve meaning across system
generations.

Open architectural questions:

- JSON-LD vs RDF/Turtle vs both?
- Which provenance ontology — PROV-O, PROV-AI, custom Sentinel
  ontology?
- Where to host the ontology canonical URL?
- Default format vs opt-in export?

No code committed. Design partner input pending.

## Item 3: Fine-grained data retention control

The need: production deployments require per-decision rules for what
raw data is stored vs hashed-only, with field-level masking and
lifecycle policies. The current binary (all-or-nothing) is too
coarse.

Open architectural questions:

- Policy declaration syntax — YAML, Python predicates, both?
- Field masking vocabulary — JSONPath, JMESPath, custom DSL?
- Policy versioning — do policies themselves require attestation?
- Integration with GDPR right-to-be-forgotten workflows?

No code committed. Design partner input pending.

## Item 4: Storage-layer integrity enforcement

The need: hash verification detects tampering after the fact. Some
compliance contexts require enforcement at the storage layer itself
— append-only, write-once, cryptographically anchored.

Open architectural questions:

- Which write-once backends to support — S3 Object Lock, Azure Blob
  immutability, GCS bucket lock, transparency.dev Merkle-tree logs,
  hardware (TPM)?
- Backend abstraction — single interface or per-backend
  specialization?
- Storage-mode metadata in attestations — how to signal "this
  attestation is on write-once storage"?
- Air-gapped scenarios — what storage primitives apply?

No code committed. Design partner input pending.

---

## Status

These four items represent v3.5 planning. Implementation begins
after architecture has been validated with at least one design
partner. The order of implementation will be determined by
design-partner priorities.
