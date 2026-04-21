# Sentinel Roadmap

Four modules. Three shipped, one on the roadmap. Every version
reflects shipped code, not plans. For the deeper strategic
picture — the Evidence Infrastructure thesis, the four-module
architecture, and the market timing — see
[docs/vision.md](vision.md).

## Phase 1: Trace + Policy + Evidence (v1.0 → v3.3) ✓

**Status: Production / stable. API frozen since v3.0 (two
documented exceptions — the v3.2.0 privacy-default flip and
the v3.3.0 positioning refinement; see
[docs/api-stability.md](api-stability.md)).**

The three shipped modules, one set of capabilities each.

### Sentinel Trace

- `@sentinel.trace` decorator, sync and async, any Python
  callable.
- Append-only, tamper-resistant `DecisionTrace` schema,
  versioned at `schema_version = 1.0.0`.
- SQLite, Filesystem (NDJSON), PostgreSQL storage backends —
  all local-first.
- Air-gapped validation suite (11 dedicated tests; socket-layer
  denial in CI).
- SHA-256 hashing on every input and output by default.
- Privacy-by-default: `store_inputs=False` / `store_outputs=False`
  by default from v3.2.0 onward.
- Trace integrity verification (`verify_integrity`), retention
  purge (`purge_before`), NDJSON export/import.

### Sentinel Policy

- Three policy evaluators: `NullPolicyEvaluator`,
  `SimpleRuleEvaluator` (Python callables),
  `LocalRegoEvaluator` (in-process OPA binary).
- Kill switch (EU AI Act Art. 14): `engage_kill_switch` /
  `disengage_kill_switch`, thread-safe, no restart required.
- Preflight checks: `sentinel.preflight(action)` without
  writing a trace.
- `SentinelManifesto` — policy-as-code declaration with
  requirement types (`EUOnly`, `Required`, `OnPremiseOnly`,
  `Targeting`, `AcknowledgedGap`, `BSIProfile`, `GDPRCompliant`,
  `RetentionPolicy`, `AuditTrailIntegrity`, `VSNfDReady`,
  `ZeroExposure`).
- Five named CI gates on every PR enforcing the above.

### Sentinel Evidence

- `sentinel evidence-pack` — signed PDF evidence packs for
  auditors. Cover page, executive summary, EU AI Act / DORA /
  NIS2 coverage, trace samples, hash manifest with pack
  digest, attestation appendix.
- `sentinel ci-check` — one-stop CI aggregator of EU AI Act
  snapshot, runtime dependency scan, and policy check.
- Provability reports (`sentinel report`) — self-contained
  HTML, no CDN, air-gap-safe.
- Portable attestations (`generate_attestation` /
  `verify_attestation`) — SHA-256 over canonical content.
- Optional long-term-retention signing via ML-DSA-65 (FIPS 204)
  and RFC-3161 timestamping through EU-sovereign TSAs (DFN-CERT,
  D-Trust). Keys stay operator-side. See
  [docs/sentinel-evidence.md](sentinel-evidence.md) for the
  detailed posture.

### v3.3 — positioning refinement

- Customer-facing language aligned to *Evidence infrastructure
  for the regulated AI era* and the *Trace. Attest. Audit.
  Comply.* formula.
- Four-module architecture (Trace / Policy / Evidence /
  Federation) replaces the earlier Three-Layer (Trace / Govern /
  Route) framing as a refinement, not reversal — Evidence is
  promoted to first-class module status because it is the primary
  artefact regulated enterprises need for BaFin and audit
  compliance.
- No code changes. No API breaks. No schema changes. The v3.3
  scope is positioning, narrative, and documentation only.

## Phase 2: Certify (v3.x, 2026)

**Status: in progress.**

| Version | Milestone                                               | Window  |
|---------|---------------------------------------------------------|---------|
| v3.x    | Linux Foundation Europe application                     | Q3 2026 |
| v3.x    | BSI IT-Grundschutz formal assessment                    | Q4 2026 |
| v3.x    | First production deployments (lighthouse customers)     | 2026    |

Phase 2 turns "technically operable under EU jurisdiction"
into "independently verifiable". LF Europe stewardship gives
the project an EU-governed home. BSI assessment produces a
profile that every German public-sector buyer can reference.

### v3.5 — Architecture Release (next months)

**Status: design.** Senior design-partner architectural review
(April 2026) confirmed four gaps that must close before
Sentinel is deployable inside modern enterprise observability
stacks. v3.5 addresses all four. Not a breaking release; the
v3.4 public API remains stable.

1. **OpenTelemetry GenAI integration** — parent-child trace
   context (`W3C Trace Context` propagation), `gen_ai.*`
   semantic attributes per the OpenTelemetry GenAI conventions,
   Sentinel attestation emitted as a span event rather than a
   sibling record. Removes the "island solution" risk; lets
   Langfuse / Phoenix / Datadog / Grafana Tempo see Sentinel
   evidence as first-class telemetry.
2. **JSON-LD + PROV-O output format** — long-term semantic
   retention. Attestations written as JSON-LD documents with
   the W3C PROV-O vocabulary mapped over the existing schema,
   so ten-year archives remain machine-interpretable by any
   PROV-aware tool regardless of Sentinel's own fate.
3. **Fine-grained retention policies** — per-decision choice of
   raw-payload vs hash-only storage. Today's privacy-by-default
   flag is global; v3.5 lets a manifesto declare "payload retain
   for credit decisions, hash-only for claims triage" based on
   GDPR Art. 6/9 legal basis and sector-specific retention law.
4. **Write-once storage backend support** — S3 Object Lock in
   compliance mode, Azure Blob Immutable Storage, POSIX append-
   only filesystem. WORM adherence for regulators that require
   cryptographic-and-operational tamper-evidence, not only
   cryptographic.

The existing ecosystem-bridge items (MCP gateway, Microsoft AGT,
Langfuse ingestion, OPA native decision-log export format,
Cedar, Redis/S3-compatible storage) remain on the roadmap as
v3.6+ work or community contributions, queued behind the four
architecture priorities above.

*(Note: the OPA *evaluator* already shipped in v3.1 — see
``LocalRegoEvaluator``. The roadmap item refers to the separate
OPA native decision-log export format that exposes Sentinel
attestations in OPA's own audit schema, distinct from evaluation.)*

## Phase 3: Federation (v4.x, roadmap)

**Status: architecturally anchored. Not committing to a ship
date yet. RFC-002 planned.**

Phase 3 is **Sentinel Federation** — the fourth module of the
product. Multi-institution aggregation: holding-group
compliance visibility, industry-consortium evidence rollup,
supervisory-body oversight across federated institutions
without individual data disclosure.

Federation is the answer to the structural question that
emerges after single-institution adoption: how do a
supervisory authority, a banking holding, or a KRITIS
coordination body gain aggregate visibility without breaking
the sovereignty of each underlying institution? The answer is
not "share the raw traces" — that would destroy the privacy
guarantee. The answer is federation: cryptographic
aggregation, selective disclosure, and schema-compatible
attestations that let an aggregator prove compliance rollup
without seeing the underlying decisions.

**Architectural anchor.** `sentinel/federation/` exists today
as a placeholder with a defined interface. The cryptographic
primitives (SHA-256 attestations, ML-DSA-65 signing) are
already shipped. The aggregation protocol is the subject of
RFC-002, to be drafted as part of Phase 3 kickoff.

**Note on model-routing / SovereignRouter.** The previously
announced Phase 3 module — SovereignRouter, policy-driven
model selection — is deferred. It may reappear as a Federation
sub-capability if and when real multi-institution deployments
surface a concrete need. It is not an independent layer.
Issue #24 has been relabeled accordingly.

## Phase 4: Ecosystem (v5.x, 2027+)

**Status: scoped, not yet started.**

The last acknowledged gap is the build pipeline itself. Phase 4
closes it.

- **EU-sovereign build pipeline** — Gitea or Forgejo instead of
  GitHub Actions. The project stops acknowledging a gap and
  stops having one.
- **EU package registry** — instead of PyPI, for the critical
  path.
- **Signed build artefacts** — end-to-end supply-chain
  verification with keys that never leave EU hardware.

## Why Sentinel is built for the long term

Every technology wave produces new systems that make
autonomous decisions. Expert systems in the 1980s. ML
classifiers in the 2000s. LLMs in the 2020s. Agentic systems
today. Neurosymbolic systems tomorrow.

Sentinel is built around the regulatory requirement, not the
technology:

> *"Every high-risk autonomous decision must be automatically
> recorded in a tamper-resistant, regulator-accepted evidence
> trail."*

This requirement does not mention LLMs. It does not mention
any specific technology. It describes a property of decision-
making systems.

`@sentinel.trace` is that property, implemented. It wrapped
expert systems in principle. It wraps LLMs today. It will
wrap whatever comes next.

## The market thesis

Three clocks align in 2026.

**The regulator.** EU AI Act Annex III high-risk enforcement
begins 2 August 2026, with penalties up to €15M or 3% of
global turnover. Every regulated European buyer needs
automatic, tamper-resistant decision logging from that date.
The procurement conversations for Q4 2026 are happening now.

**The sovereignty moment.** *"EU-jurisdictional"* has stopped
being marketing and started being a purchase criterion. BSI
publishes reference profiles. LF Europe exists to host
projects under EU governance. The infrastructure to be
credibly operated under EU jurisdiction exists for the first
time.

**The empty field.** No EU-operated, open-source, model-
agnostic, cryptographically-provable decision infrastructure
exists today. US competitors cannot occupy this category
because US incorporation means CLOUD Act exposure on every
evidence record. The field is empty; the regulation creates
demand; Sentinel fills the intersection.

That is the roadmap. Ship Trace, Policy, and Evidence (done).
Certify in Phase 2. Build Federation when the first real
multi-institution scenarios surface. Close the build pipeline
when the rest matures. The destination is a thin, open,
auditable infrastructure any European enterprise can run
under its own law, with any decision system, with a record a
BSI auditor accepts.
