# LLMOps and AI Agent Landscape

Sentinel sits at the intersection of LLM tracing and enterprise governance. This document clarifies where it fits, what it does not do, and where it is headed.

---

## Current landscape (2026)

| Category | Examples | What they do | Sentinel |
|---|---|---|---|
| **LLMOps / Tracing** | Langfuse, LangSmith, Phoenix, Helicone | Debug LLM calls, latency/cost metrics, prompt iteration, evals | **No** — does not trace individual LLM calls or provide dev debugging |
| **AI Agent Frameworks** | LangGraph, CrewAI, AutoGen, Semantic Kernel | Build agent workflows and state machines | **No** — does not build agents, wraps them for governance |
| **Enterprise Platforms** | Proprietary full-stack AI platforms with built-in decision layers | End-to-end AI deployment with vendor-controlled decision recording | **Designed for** — sovereign decision record layer for deployments where proprietary platforms are jurisdictionally excluded |
| **Prompt Management** | Langfuse Prompt Mgmt, PromptLayer, Humanloop | Version prompts, A/B test, human-in-loop iteration | **No** — does not manage prompts or do prompt engineering |
| **Eval Frameworks** | DeepEval, RAGAS, UpTrain | LLM output quality scoring, RAG evaluation | **No** — does not score LLM quality or run evals |
| **Observability** | OpenTelemetry, Grafana, Datadog | General infrastructure monitoring, distributed tracing | **Partial** — OTel export planned as optional extra; traces are currently native JSON/NDJSON |

**Relationship key:** *Complementary* = works alongside. *Upstream* = Sentinel wraps or builds on it. *Downstream* = consumes Sentinel output. *Adjacent* = different problem, no overlap. *Designed for* = Sentinel addresses this category's gap.

---

## What Sentinel does

Sentinel occupies a category that does not have an established name yet: **decision record infrastructure**. It produces a structured, append-only, sovereign artifact for every autonomous decision — capturing what was decided, under which policy, by which system, and under whose jurisdiction.

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
| LangGraph / CrewAI / AutoGen | `@sentinel.trace` decorator on agent entry points |
| Any LLM provider | Model metadata recorded in trace (set explicitly) |
| OPA / Rego policies | `LocalRegoEvaluator` — in-process, no network |
| Python rule functions | `SimpleRuleEvaluator` — zero dependencies |
| OpenTelemetry | Planned export as optional extra (`sentinel-kernel[otel]`) |

Framework-specific integration helpers (LangChain, LangGraph) are planned for v0.3.

---

## Current flow

```
Agent → sentinel.trace() → SQLite / NDJSON trace
                ↓ (planned)
           OTEL → Langfuse / Grafana
```

Today, traces are written to local storage only. OpenTelemetry export is a planned optional extra (`sentinel-kernel[otel]`) — not yet implemented.

---

## Why a separate layer

Observability tools record what happened. Sentinel records what was *decided* — and attaches policy evaluation, sovereignty metadata, and human override records that make the trace legally meaningful under EU AI Act Article 12.

The distinction matters in regulated environments:

- An observability trace says "the model returned this output in 312ms."
- A Sentinel trace says "this agent decided to approve this request, under this policy, which returned ALLOW, with inputs hashed as SHA-256, stored on EU-DE infrastructure, at this timestamp, with this schema version."

The second is what a regulator, auditor, or court needs.
