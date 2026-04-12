# Sentinel Roadmap

Three phases. Every version reflects shipped code, not plans.

For the deeper strategic picture — the Sovereign Decision Kernel architecture,
the Palantir thesis, and the market timing — see
[docs/vision.md](vision.md).

## Phase 1: Trace + Govern (v1.0–v3.0) ✓

**Status: Production / stable. API frozen as of v3.0.**

The kernel and every governance primitive around it.

- **v1.0** — Core kernel. Sentinel interceptor, DecisionTrace, SQLite and
  Filesystem storage, in-process policy evaluation, kill switch (EU AI Act
  Art. 14), full async and sync support.
- **v1.5** — Compliance checkers. EU AI Act, DORA, NIS2. BSI profile and
  VS-NfD deployment guide.
- **v2.0** — Manifesto-as-code. `SentinelManifesto`, sovereignty scanner,
  five named CI theses, full CLI (`sentinel scan`, `sentinel demo`,
  `sentinel report`). Production stable.
- **v2.1** — BudgetTracker, portable attestations, CrewAI and AutoGen
  integrations, preflight checks.
- **v2.2** — Quantum-safe signing. ML-DSA-65 (FIPS 204), BSI TR-02102-1
  recommended. RFC 3161 timestamping with EU-only TSAs.
- **v2.3** — LangFuse sovereignty panel (self-contained HTML widget,
  no CDN).
- **v2.4** — RFC-001 `SovereigntyManifest` Rust reference implementation.
- **v3.0** — API freeze. BSI pre-engagement package ready. v1→v3
  capability parity on the public site. 608 tests, 100% coverage.
- **v3.0.1 / v3.0.2** — Reentrant scanner timeout, workflow concurrency
  guards, walk-time directory pruning. Operational hardening.

## Phase 2: Certify (v3.1–v3.x, 2026)

**Status: in progress.**

| Version | Milestone                                               | Window  |
|---------|---------------------------------------------------------|---------|
| v3.1    | Linux Foundation Europe application                     | Q3 2026 |
| v3.2    | BSI IT-Grundschutz formal assessment                    | Q4 2026 |
| v3.x    | First production deployments (lighthouse customers)     | 2026    |
| v3.x    | Go + TypeScript RFC-001 implementations                 | 2026    |

Phase 2 exists to turn "technically sovereign" into "independently
verifiable." LF Europe stewardship gives the project an EU-governed
home. BSI assessment produces a profile that every German public-sector
buyer can reference. The multi-language RFC-001 implementations take
SovereigntyManifest from a Python library to a cross-ecosystem standard.

## Phase 3: Route (v4.x, 2026–2027)

**Status: design / RFC-002 in progress.**

Phase 3 is the **SovereignRouter** — the third layer of the Sentinel
Kernel. The thesis is simple: your SentinelManifesto already defines
which systems are permitted for each data class. The router reuses the
same policy engine to select the right decision system automatically.

The router is technology-agnostic by design. The same policy that decides
"this data is classified, use a local model" also decides "this decision
requires a deterministic rule engine, not a probabilistic LLM." The
router selects the right system for the right decision — not just between
LLMs, but between any decision system in your inventory.

```python
# Define once in your manifesto:
class OurPolicy(SentinelManifesto):
    models = ModelPolicy(
        public_data=["claude-3", "mistral-api", "gpt-4"],
        internal_data=["mistral-eu-hosted", "azure-eu"],
        confidential=["llama3-70b-local", "mistral-local"],
        classified=["llama3-70b-airgapped"],   # offline only
    )

# Use everywhere:
result = await sentinel.route(
    task="process_document",
    context={"classification": "confidential"},
)
# → automatically uses llama3-70b-local
# → records: model, why, sovereignty proof in the DecisionTrace
```

| Version | Milestone                                                          |
|---------|--------------------------------------------------------------------|
| v4.0    | `SovereignRouter`, `ModelPolicy`, policy-driven model selection    |
| v4.1    | Local adapters: Ollama, vLLM, llama.cpp                            |
| v4.2    | Multi-model consensus for high-stakes decisions                    |
| v4.3    | LLM-guided deployment — the kernel self-configures new pipelines   |

RFC-002 (`SovereignRouter`) is the formal design gate for Phase 3.
See the RFC-002 GitHub Discussion for the open questions and comment
window.

## Phase 4: Ecosystem (v5.x, 2027+)

**Status: scoped, not yet started.**

The last acknowledged gap is the build pipeline itself. Phase 4 closes it.

- **EU-sovereign build pipeline** — Gitea or Forgejo instead of GitHub
  Actions. The project stops acknowledging a gap and stops having one.
- **EU package registry** — instead of PyPI, for the critical path.
- **Signed build artifacts** — end-to-end supply-chain verification,
  with keys that never leave EU hardware.
- **Multi-language parity** — Python, Rust, Go, TypeScript all at
  first-class status, not just manifest implementations.

## Why Sentinel is built for the long term

Every technology wave produces new systems that make autonomous decisions.
Expert systems in the 1980s. ML classifiers in the 2000s. LLMs in the
2020s. Agentic systems today. Neurosymbolic systems tomorrow.

Sentinel is built around the regulatory requirement, not the technology:

> "Every high-risk autonomous decision must be automatically recorded
> in a tamper-resistant, sovereign audit trail."

This requirement does not mention LLMs. It does not mention any specific
technology. It describes a property of decision-making systems.

`@sentinel.trace` is that property, implemented. It wrapped expert systems
in principle. It wraps LLMs today. It will wrap whatever comes next.

## The market thesis

Three clocks line up in 2026.

**The regulator.** EU AI Act Annex III high-risk enforcement begins
2 August 2026, with penalties up to €15M or 3% of global turnover.
Every regulated European buyer needs automatic, tamper-resistant decision
logging from that date. The procurement conversations for Q4 2026 are
happening now.

**The sovereignty moment.** "EU-sovereign" has stopped being marketing
and started being a purchase criterion. BSI publishes reference profiles.
LF Europe exists to host projects under EU governance. The infrastructure
to be credibly sovereign exists for the first time.

**The empty field.** Palantir AIP costs €5–20M per year, is
US-incorporated, and requires deployment strategists. When LLMs guide
their own integration — and that is already happening — the
deployment-strategist model collapses. What survives is the trusted
kernel underneath: policy, audit trail, model router, sovereignty proof.
Nobody else is building this as an open-source, EU-sovereign,
model-agnostic kernel. The field is empty and the regulation creates
the demand.

That is the roadmap. Ship Phase 1, certify in Phase 2, build the router
in Phase 3, close the build pipeline in Phase 4. The destination is a
thin, open, auditable kernel that any European enterprise can run under
its own law, with any model, with a decision record good enough for a
BSI auditor.
