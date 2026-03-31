# Sentinel

**EU-sovereign AI decision middleware. Open source. Foundation governed.**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)
[![OpenTelemetry](https://img.shields.io/badge/traces-OpenTelemetry-blueviolet)](https://opentelemetry.io)
[![Linux Foundation Europe](https://img.shields.io/badge/governance-LF%20Europe%20candidate-003366)](https://linuxfoundation.eu)
[![Discord](https://img.shields.io/badge/community-Discord-5865F2)](https://discord.gg/sentinel-kernel)

---

Every AI agent your enterprise runs makes decisions. Approves a discount. Routes an escalation. Grants an exception. Denies access.

Those decisions are currently invisible.

**Sentinel sits in the execution path of your AI agents and makes every decision a first-class, sovereign, auditable artifact** — without locking you into a platform, a cloud, or a country.

```python
from sentinel import Sentinel

sentinel = Sentinel(storage="sqlite:///decisions.db")

@sentinel.trace
async def approve_discount(deal: Deal, request: DiscountRequest) -> Decision:
    # Your existing agent logic — unchanged
    return await agent.evaluate(deal, request)
```

That's it. Every call now produces a structured decision trace: what inputs were seen, which policy was evaluated, what exception was granted, who approved, and why. Queryable. Replayable. Sovereign.

---

## Why Sentinel exists

The next generation of enterprise software will be built by whoever captures **decision traces** — the exceptions, overrides, and cross-system context that currently die in Slack threads, Zoom calls, and people's heads.

Palantir understands this. Their AIP platform is exactly this — a decision trace layer that becomes the system of record for enterprise intelligence. It's excellent engineering.

It's also American. Deeply so.

For European regulated industries — financial services, healthcare, defence, critical infrastructure — a US-owned system of record for AI decisions is not a procurement preference. It's a structural barrier. GDPR, the EU AI Act (August 2026), DORA, NIS2, and emerging CADA requirements mean these organisations need a context graph they legally and politically control.

Sentinel is the answer: **the open source, EU-sovereign context graph middleware that no American company can replicate, because the sovereignty is the product.**

---

## Architecture

Sentinel is a kernel, not a platform. It does one thing precisely: **sit in the execution path and capture decision traces**.

```
┌─────────────────────────────────────────────────────┐
│                   Your AI Agents                     │
│         (LangGraph / CrewAI / AutoGen / custom)      │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │     Sentinel Kernel     │
          │                         │
          │  ┌─────────────────┐   │
          │  │   Interceptor   │   │  ← Wraps any agent call
          │  └────────┬────────┘   │
          │           │            │
          │  ┌────────▼────────┐   │
          │  │  Policy Eval    │   │  ← OPA-compatible Rego
          │  └────────┬────────┘   │
          │           │            │
          │  ┌────────▼────────┐   │
          │  │ Trace Emission  │   │  ← OpenTelemetry spans
          │  └────────┬────────┘   │
          │           │            │
          │  ┌────────▼────────┐   │
          │  │ Storage Backend │   │  ← SQLite / D1 / Postgres / FS
          │  └─────────────────┘   │
          └─────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Any LLM Provider                        │
│    (Anthropic / Mistral / Ollama / Azure OAI)        │
└─────────────────────────────────────────────────────┘
```

### Design principles

- **Standard formats only.** Traces are OpenTelemetry spans with Sentinel semantic conventions. No proprietary format.
- **Pluggable storage.** SQLite for local dev, Cloudflare D1 for edge sovereign, Postgres for enterprise on-prem, filesystem for air-gapped.
- **Policy-as-code via OPA.** Write Rego rules. Sentinel evaluates at decision time and records the result.
- **Framework-agnostic.** Integrations for LangGraph, CrewAI, AutoGen, and bare OpenAI/Anthropic clients. If it makes an LLM call, Sentinel can wrap it.
- **Single binary.** No cloud account required to get started. `pip install sentinel-kernel` and go.

---

## Quickstart

```bash
pip install sentinel-kernel
```

```python
from sentinel import Sentinel
from sentinel.storage import SQLiteStorage

# Initialise with local storage
sentinel = Sentinel(
    storage=SQLiteStorage("./decisions.db"),
    project="my-first-agent",
)

# Decorate any function that makes an AI decision
@sentinel.trace(policy="policies/default.rego")
async def classify_support_ticket(ticket: str) -> dict:
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": f"Classify: {ticket}"}]
    )
    return {"classification": response.choices[0].message.content}

# Run it
result = await classify_support_ticket("Customer can't log in after password reset")

# Every call is now a sovereign trace
traces = sentinel.storage.query(project="my-first-agent", limit=10)
print(traces[0].to_dict())
# {
#   "trace_id": "0af7651916cd43dd8448eb211c80319c",
#   "timestamp": "2026-04-01T11:23:41.234Z",
#   "agent": "classify_support_ticket",
#   "policy": "default",
#   "policy_result": "ALLOW",
#   "model": "gpt-4o",
#   "inputs": {"ticket": "Customer can't log in..."},
#   "output": {"classification": "auth/password-reset"},
#   "latency_ms": 847,
#   "sovereign_scope": "EU",
#   "data_residency": "local"
# }
```

**Time to first trace: under 5 minutes.**

---

## Integrations

### LangGraph

```python
from sentinel.integrations.langgraph import SentinelLangGraphMiddleware

graph = StateGraph(AgentState)
graph.add_middleware(SentinelLangGraphMiddleware(sentinel))
```

### CrewAI

```python
from sentinel.integrations.crewai import SentinelCrewObserver

crew = Crew(agents=[...], tasks=[...])
crew.add_observer(SentinelCrewObserver(sentinel))
```

### Anthropic

```python
from sentinel.integrations.anthropic import SentinelAnthropicClient

client = SentinelAnthropicClient(sentinel, api_key="...")
# Drop-in replacement — all calls traced automatically
```

---

## Storage backends

| Backend | Use case | Sovereign |
|---|---|---|
| `SQLiteStorage` | Local development, single node | ✓ |
| `CloudflareD1Storage` | Edge sovereign, Cloudflare Workers | ✓ EU data residency |
| `PostgresStorage` | Enterprise on-prem | ✓ |
| `FilesystemStorage` | Air-gapped, classified environments | ✓ No network |

```python
# Edge sovereign — runs on Cloudflare Workers at EU data centres
from sentinel.storage import CloudflareD1Storage
storage = CloudflareD1Storage(database_id="...", account_id="...")

# Air-gapped — writes NDJSON to disk, no network required
from sentinel.storage import FilesystemStorage
storage = FilesystemStorage("/mnt/classified/traces/")
```

---

## Policy-as-code

Sentinel evaluates policies at decision time using OPA-compatible Rego. The evaluation result is part of the trace.

```rego
# policies/discount_approval.rego
package sentinel.discount

default allow = false

allow {
    input.request.discount_pct <= 10
}

allow {
    input.request.discount_pct <= 25
    input.customer.tier == "enterprise"
}

# Exception requires VP approval
exception_required {
    input.request.discount_pct > 25
}
```

```python
@sentinel.trace(policy="policies/discount_approval.rego")
async def approve_discount(deal, request):
    ...
```

When the policy blocks an action, Sentinel records `policy_result: DENY` with the rule that triggered it. When a human overrides, that override is the next trace entry — creating a permanent, queryable chain of precedent.

---

## EU AI Act compliance

Sentinel is designed to satisfy Article 12 of the EU AI Act (automatic logging for high-risk AI systems) and Article 17 (quality management traceability requirements) out of the box.

Every trace includes:
- Timestamp and duration
- Model version and provider
- Input data hash (no PII stored unless configured)
- Policy evaluated and result
- Human override record (if applicable)
- Data residency assertion

Full compliance mapping in [`docs/eu-ai-act.md`](docs/eu-ai-act.md).

---

## Deployment

### On-premise (single command)

```bash
docker run -p 4317:4317 -v /data/traces:/data \
  ghcr.io/sentinel-kernel/sentinel:latest
```

### Cloudflare Workers (edge sovereign)

```bash
npx wrangler deploy --config sentinel.wrangler.toml
```

### Air-gapped

```bash
sentinel-cli init --storage filesystem --path /mnt/traces
sentinel-cli export --format ndjson --output /mnt/export/audit-$(date +%Y%m).ndjson
```

---

## Governance

Sentinel is governed independently of any commercial entity.

- **License:** Apache 2.0, permanently. No BSL. No license changes.
- **Governance:** Applying to Linux Foundation Europe (Q2 2026)
- **Funding:** Sovereign Tech Fonds application in progress
- **Trademark:** Sentinel trademark held by foundation, not a company

Major changes go through an **RFC process**: open a GitHub Discussion, 14-day comment period, maintainer vote. No single company controls the roadmap.

---

## Contributing

Sentinel is built by and for the European AI community. We welcome contributions from individuals, universities, research institutions, and companies.

**First contribution?** Look for issues labelled [`good first issue`](https://github.com/sebastianweiss83/sentinel-kernel/issues?q=label%3A%22good+first+issue%22).

**Building an integration?** Read [`docs/integration-guide.md`](docs/integration-guide.md) and open a PR.

**Representing an organisation?** Read [`docs/co-innovation.md`](docs/co-innovation.md) about joining the co-innovation council.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for full guidelines.

---

## Roadmap

| Milestone | Target | Status |
|---|---|---|
| v0.1 — Kernel + SQLite + OTel | Q2 2026 | 🔨 In progress |
| v0.2 — Cloudflare D1 + Workers | Q2 2026 | Planned |
| v0.3 — LangGraph + CrewAI integrations | Q3 2026 | Planned |
| v0.4 — Air-gapped / filesystem backend | Q3 2026 | Planned |
| v1.0 — BSI reference implementation | Q4 2026 | Planned |
| v1.1 — VS-NfD deployment profile | Q1 2027 | Planned |

---

## Community

- **Discord:** [discord.gg/sentinel-kernel](https://discord.gg/sentinel-kernel)
- **GitHub Discussions:** For RFCs and architecture questions
- **Monthly call:** First Tuesday of each month, open to all

---

## Who is using Sentinel

*Early design partners (reference deployments forthcoming)*

- **Quantum Systems** — autonomous systems, classified environments
- *Your organisation here — [open an issue](https://github.com/sebastianweiss83/sentinel-kernel/issues/new?template=design-partner.md)*

---

## License

Apache 2.0. See [LICENSE](LICENSE).

The Sentinel name and logo are trademarks of the Sentinel Foundation (in formation). They may be used in accordance with the [Trademark Policy](docs/trademark.md).
