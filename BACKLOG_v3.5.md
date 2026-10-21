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

## Item 5: Signed attestations for AI code attribution

The need: AI agents now write a growing share of the code that runs
in regulated systems. Auditors increasingly ask who authored that
code — a human or an AI agent — under which policy, and who approved
it. Open attribution formats (for example the Agent Trace
specification) record which lines an agent produced and link them
to the originating conversation. They do not make that record
tamper-resistant: an attribution log can be edited or dropped after
the fact.

Sentinel's role would be the evidence layer on top of such a format,
not a competing format: sign and timestamp attribution records so
they become verifiable evidence instead of editable logs.

Scope boundary: this targets code shipped into regulated systems,
where the organisation controls the toolchain. It does not try to
verify contributions from untrusted outside contributors — that
record can only be captured on the contributor's machine and cannot
be enforced.

Open architectural questions:

- Which attribution format(s) to accept as input — Agent Trace only,
  or an adapter interface?
- Attest per commit, per pull request, or per release?
- Where does signing happen — CI pipeline, merge hook, or release
  build?
- How does code attribution map to existing `DecisionTrace` fields,
  or does it need its own record type (RFC required)?

No code committed. To be validated with design partners before
prioritising against Items 1–4.

---

## Status

Items 1–4 represent v3.5 planning; Item 5 is a candidate, not yet
prioritised. Implementation begins
after architecture has been validated with at least one design
partner. The order of implementation will be determined by
design-partner priorities.
