# Roadmap

Sentinel's roadmap is shaped by one deadline: **EU AI Act Article 12 logging obligations apply from 2 August 2026.** Every milestone exists to make that deadline achievable for teams deploying AI agents in regulated European environments.

For the broader strategic vision and core beliefs, see [VISION.md](VISION.md).

---

## Where Sentinel is today

**v0.1 — Alpha (current)**

Sentinel is an open, EU-native, lightweight decision trace kernel. It captures structured, append-only decision records from any AI agent function, evaluates policy in-process, and stores traces locally with zero network dependencies.

What works now:
- `@sentinel.trace` decorator (sync and async)
- Three policy evaluators: NullPolicy, SimpleRule, LocalRego (OPA)
- Two storage backends: SQLite, Filesystem (NDJSON)
- SHA-256 hashed inputs and outputs
- Human override model with linked trace entries
- Data residency and sovereignty metadata on every trace
- 71 tests, 86% coverage

What is missing: no ontology, no dashboard, no enterprise deployment tooling, no framework integrations. This is intentional — the kernel must be correct before it is convenient.

---

## 2026 — Production-ready kernel

### v0.2 — Storage and schema hardening

- PostgreSQL storage backend (enterprise deployments)
- Schema migration tooling (safe upgrades between versions)
- CLI (`sentinel` command) for trace inspection and export
- Trace schema ratified (v1.0.0 from draft)

### v0.3 — Framework integrations and export

- LangChain / LangGraph integration (`sentinel-kernel[langchain]`)
- OpenTelemetry export (`sentinel-kernel[otel]`) — traces flow to Langfuse, Grafana, or any OTel-compatible backend
- `SovereigntyViolationError` enforcement at runtime
- Expanded test coverage: 95%+ on core, 90%+ on storage

### v0.4 — Compliance and certification readiness

- BSI IT-Grundschutz reference architecture published
- EU AI Act Article 12/13/17 compliance test suite (machine-verifiable)
- Security audit by independent third party
- Air-gapped deployment guide with reproducible verification

### v1.0 — Production release

- Stable public API with semantic versioning guarantees
- Linux Foundation Europe project acceptance
- Production deployments in EU regulated industries
- BSI-aligned reference architecture for German regulated sectors

**Design partners shape v0.2–v0.4.** Real deployment feedback from regulated industries determines which features ship and in what order.

---

## 2027 — Reference implementation

- VS-NfD deployment profile for classified German government use cases
- Official BSI guidance referencing Sentinel as a reference implementation
- Co-innovation contributions from European enterprises and research institutions (T-Systems, Fraunhofer, BWI, and others)
- Sovereign Tech Fonds-funded core maintainer team
- 5+ production deployments across EU regulated sectors

By 2027, EU AI Act enforcement is in full effect. Sentinel's goal is to be the implementation that regulators point at when asked "what does compliant Article 12 logging look like?"

---

## 2028+ — European standard

- De facto open standard for AI decision trace infrastructure in Europe
- VS-NfD certified for classified environments
- Commercial ecosystem of certified deployment partners and vertical applications built on the kernel
- Foundation governance fully independent of any single company
- Standard written in production — shaped by the organisations that shipped first

---

## What Sentinel will never build

These are permanent scope boundaries, not deferred features:

- No hosted SaaS product inside the open source project
- No dashboard or UI (commercial products built on Sentinel may provide these)
- No model serving, fine-tuning, or inference pipeline
- No content moderation or output filtering
- No proprietary extensions or enterprise edition

Commercial products built on Sentinel are welcome and expected. They do not live in this repository.

---

## Competitive context

Sentinel occupies a category — **decision record infrastructure** — that sits between observability platforms and sovereign cloud platforms. It is not competing with either.

| Layer | Examples | What Sentinel does |
|---|---|---|
| **Sovereign cloud platforms** | Full-stack sovereign AI runtimes with infrastructure, model hosting, and governance layers | Deploys *on* these platforms. Every agent running on sovereign infrastructure still needs Article 12 decision logging — Sentinel provides it. |
| **LLMOps / Observability** | Langfuse, LangSmith, Helicone, Phoenix | Complementary. LLMOps answers "why is my agent slow?" Sentinel answers "what did my agent decide, and can I prove it to a regulator?" |
| **AI Agent Frameworks** | LangGraph, CrewAI, AutoGen | Upstream. Sentinel wraps agent frameworks for governance — it does not replace them. |
| **Enterprise AI Platforms** | Proprietary full-stack platforms with vendor-controlled decision layers | Alternative for deployments where proprietary platforms are jurisdictionally excluded under CLOUD Act exposure. |

The structural moat: **Apache 2.0 forever + BSI certified + production decision traces nobody else has.**

---

## How to influence the roadmap

1. **Deploy it.** Real deployment feedback outweighs all other input.
2. **File issues.** Missing schema fields, broken offline paths, storage gaps.
3. **Open an RFC.** Architectural opinions welcome via the [RFC process](CONTRIBUTING.md).
4. **Bring a use case.** If your organisation has a regulated deployment context, open a [GitHub Discussion](https://github.com/sebastianweiss83/sentinel-kernel/discussions).

The roadmap is not a promise — it is a plan shaped by the organisations willing to ship first.
