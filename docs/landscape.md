# LLMOps and AI Agent Landscape

Sentinel sits at the intersection of LLM tracing and regulated-enterprise infrastructure. This document clarifies where it fits, what it does not do, and where it is headed. For the strategic framing — evidence infrastructure for the regulated AI era, the Trace / Attest / Audit / Comply formula, the four modules — see [docs/vision.md](vision.md).

---

## Current landscape (2026)

| Category | Examples | What they do | Sentinel |
|---|---|---|---|
| **LLMOps / Tracing** | Langfuse, LangSmith, Phoenix, Helicone | Debug LLM calls, latency/cost metrics, prompt iteration, evals | **Complementary** — does not trace individual LLM calls or provide dev debugging; LangFuse ships a Sentinel-compatible integration |
| **AI Agent Frameworks** | LangGraph, CrewAI, AutoGen, Semantic Kernel | Build agent workflows and state machines | **Complementary** — does not build agents, wraps them for policy + evidence |
| **AI agent governance (closed beta)** | Dome Systems | Runtime control layer for enterprise agent fleets | **Adjacent** — Dome Systems is US-incorporated, structurally subject to US jurisdictional regimes including the CLOUD Act; Sentinel is the EU-jurisdictional alternative |
| **AI agent governance (OSS)** | Microsoft Agent Governance Toolkit | OWASP Agentic Top-10 coverage for LangChain / CrewAI / Dify | **Complementary for Microsoft-first shops** — MS AGT is US-incorporated; Sentinel is the answer when EU-jurisdictional evidence is required |
| **Sovereignty-first cybersecurity** | Cylake | Hardware + software for sovereign agent environments at national scale | **Adjacent** — Cylake is US-incorporated, positioned around sovereignty-themed cybersecurity messaging; Sentinel leads with *Provability* instead |
| **Native cloud governance** | Azure AI Foundry, AWS Bedrock Guardrails, GCP Vertex AI | Deeply cloud-integrated policy and observability | **Multi-cloud clasp** — excellent per-cloud; loses value in multi-cloud / on-premise / air-gapped scenarios |
| **Enterprise Platforms** | Proprietary full-stack AI platforms with built-in decision layers | End-to-end AI deployment with vendor-controlled decision recording | **Alternative** — auditor-grade evidence layer for deployments where proprietary platforms are jurisdictionally excluded |
| **GRC platforms** | Sastrify, Enactia, Kovrr, ADOGRC | Inventory, risk classification, and management of AI systems | **Partner candidates**, not competitors — runtime layer (Sentinel) vs. inventory layer (GRC) |
| **Prompt Management** | Langfuse Prompt Mgmt, PromptLayer, Humanloop | Version prompts, A/B test, human-in-loop iteration | **No** — does not manage prompts or do prompt engineering |
| **Eval Frameworks** | DeepEval, RAGAS, UpTrain | LLM output quality scoring, RAG evaluation | **No** — does not score LLM quality or run evals |
| **Observability** | OpenTelemetry, Grafana, Datadog | General infrastructure monitoring, distributed tracing | **Complementary** — OTel export shipped as `sentinel-kernel[otel]`; native JSON/NDJSON remains the primary format |

**Relationship key:** *Complementary* = works alongside. *Upstream* = Sentinel wraps or builds on it. *Downstream* = consumes Sentinel output. *Adjacent* = different problem, no overlap. *Designed for* = Sentinel addresses this category's gap.

---

## What Sentinel does

Sentinel occupies a category with a distinctive shape: **evidence infrastructure for the regulated AI era**. It produces a structured, append-only, auditor-grade artefact for every autonomous decision — capturing what was decided, under which policy, by which system, and under whose jurisdiction.

This is complementary to observability and LLMOps, not competing with them. A team can use Langfuse for prompt debugging and Sentinel for compliance records. They answer different questions:

| Question | Answered by |
|---|---|
| Why is my agent slow? | LLMOps / observability |
| Is this prompt performing well? | Eval frameworks |
| What did my agent decide, and can I prove it to a regulator? | Sentinel |

---

## Integration points

Sentinel wraps agent function calls. It does not require replacing your existing stack.

| If you use | Sentinel integrates via |
|---|---|
| LangChain | `sentinel-kernel[langchain]` — shipped callback handler |
| CrewAI / AutoGen | `sentinel-kernel[crewai]` / `[autogen]` — shipped task hooks |
| Haystack | `sentinel-kernel[haystack]` — shipped component wrapper |
| LangFuse | `sentinel-kernel[langfuse]` — shipped sovereignty panel |
| OpenTelemetry | `sentinel-kernel[otel]` — shipped span exporter |
| Prometheus | `sentinel-kernel[prometheus]` — shipped textfile collector |
| FastAPI / Django / Jupyter | `[fastapi]` / `[django]` / `[jupyter]` — shipped middlewares |
| Any LLM provider | Model metadata recorded in trace (set explicitly) |
| OPA / Rego policies | `LocalRegoEvaluator` — in-process, no network |
| Python rule functions | `SimpleRuleEvaluator` — zero dependencies |

LangGraph and PydanticAI integrations are explicitly postponed — see
the `Intentionally postponed` section of the v3.1.0 CHANGELOG entry.

---

## Current flow

```
Agent → sentinel.trace() → SQLite / NDJSON trace
                ↓ (optional)
           OTEL → Langfuse / Grafana
```

Traces are always written to local sovereign storage first. OpenTelemetry
export is shipped as an optional extra (`sentinel-kernel[otel]`) and
runs downstream of the local write — the local record is the source of
truth and cannot be gated by the exporter.

---

## Why a separate layer

Observability tools record what happened. Sentinel records what was *decided* — and attaches policy evaluation, jurisdictional metadata, and human override records that make the trace legally meaningful under EU AI Act Article 12.

The distinction matters in regulated environments:

- An observability trace says "the model returned this output in 312ms."
- A Sentinel trace says "this agent decided to approve this request, under this policy, which returned ALLOW, with inputs hashed as SHA-256, stored on EU-DE infrastructure, at this timestamp, with this schema version."

The second is what a regulator, auditor, or court needs.

## The gap in this landscape

Manifesto Chapter VIII names the gap explicitly: **no other
solution simultaneously offers model-spanning consistency, EU
jurisdiction for evidence, open source with exit capability, and
cryptographic provability in a regulation-mapped format.**

Sentinel sits precisely in this intersection. LLMOps tools watch
performance, not decisions. Cloud governance is locked to one
cloud. Closed-beta governance platforms are US-incorporated.
Sovereignty-first cybersecurity leads with the wrong noun. GRC
platforms manage AI systems, they do not sit in the runtime path
of a decision.

That is the category Sentinel occupies. See
[docs/vision.md](vision.md) for the full strategic framing.
