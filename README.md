# Sentinel

**The EU-sovereign decision record layer for AI agents.**

Every AI agent your organisation runs makes decisions. Approves a request.
Routes an exception. Grants access. Those decisions are currently invisible.
Sentinel makes them sovereign, auditable, and legally yours.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%2012%2F13%2F17-green.svg)](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689)
[![Governance](https://img.shields.io/badge/governance-LF%20Europe%20candidate-003366.svg)](https://linuxfoundation.eu)
[![Schema](https://img.shields.io/badge/schema-v0.1-lightgrey.svg)](docs/schema.md)

---

## What it is

Sentinel is a **middleware kernel** — a thin layer that wraps any AI agent
call, evaluates a policy in-process, and records a structured, tamper-resistant
decision trace. It does not filter content. It does not route traffic. It does
not depend on any cloud provider. It produces a sovereign artifact: a permanent,
portable record of what was decided, by which model, under which policy, and
under whose law.

```
Your agent calls Sentinel.
Sentinel evaluates your policy.
Sentinel records the decision.
Your agent proceeds.
```

The trace belongs to you — not to a platform, not to a provider,
not to a jurisdiction you did not choose.

---

## Who it is for

**If you build AI systems that touch regulated decisions** — in defence,
critical infrastructure, financial services, or healthcare — Sentinel is
your compliance foundation.

**If you deploy in environments where US jurisdiction is a blocker** —
classified networks, sovereign infrastructure, air-gapped systems —
Sentinel is the only governance layer designed for those constraints from
the ground up.

**If you need to answer a regulator, a procurement committee, or a court**
with a complete, verifiable record of every AI decision in your system,
Sentinel gives you that record.

Three personas use Sentinel:

| Persona | What they need | What Sentinel gives them |
|---|---|---|
| **Founder / CTO** | Architecture that does not create a new dependency trap | A kernel they own and control, Apache 2.0 forever |
| **Enterprise architect** | Proof that AI decisions are traceable and auditable | Structured decision traces mapped to EU AI Act articles |
| **Sovereign operator** | A system that works in classified, air-gapped environments | Full offline operation, local storage, no external calls |

---

## Why now

**August 2, 2026.** That is the enforcement date for EU AI Act requirements
on Annex III high-risk AI systems (Regulation EU 2024/1689). From that date,
organisations deploying AI in high-risk categories — which includes defence,
critical infrastructure, biometric systems, and AI in law enforcement — must
demonstrate automatic, tamper-resistant logging of all system events
(Article 12), transparency to deployers (Article 13), and human oversight
mechanisms (Article 14). Failure carries penalties of up to €15 million or
3% of global annual turnover.

No US-hosted governance tool can satisfy these requirements from its current
jurisdiction. The US CLOUD Act means any service owned by a US entity is
subject to US government access regardless of where the server sits.
An EU data centre operated by a US company does not solve this.

**The governance layer space is crowded.** Observability tools, content
filters, policy engines, and agent orchestration frameworks all offer pieces
of this. None are designed for classified deployments. None produce
legally-valid audit trails under EU jurisdiction. None have a certification
path to BSI IT-Grundschutz or VS-NfD. Sentinel does not compete with those
tools — it sits below them in the stack, recording what actually happened,
in a place those tools cannot reach.

Standardisation in this space will not happen by consensus alone. It requires
a neutral governance foundation — which is why Sentinel is pursuing Linux
Foundation Europe stewardship — and real production deployments that define
what the protocol actually needs to handle. The first design partners are
shaping that protocol now.

---

## Five-minute quick start

```bash
pip install sentinel-kernel
```

```python
from sentinel import Sentinel

# Local storage by default — works with no cloud account, no network
sentinel = Sentinel()

@sentinel.trace(policy="policies/default.rego")
async def evaluate_request(context: dict) -> dict:
    # Your existing agent logic — completely unchanged
    result = await your_model.call(context)
    return result

# Run it
outcome = await evaluate_request({"action": "approve", "amount": 50000})
```

Every call now produces a decision trace. That trace is written to local
storage, can be exported as NDJSON, and satisfies EU AI Act Article 12
logging requirements out of the box.

**Time to first trace: under five minutes.**

---

## Example trace output

This is what Sentinel records for every agent decision:

```json
{
  "trace_id": "01hx7k9m2n3p4q5r6s7t8u9v0w",
  "timestamp": "2026-04-01T14:23:41.234Z",
  "latency_ms": 312,

  "agent": "evaluate_request",
  "agent_version": "2.1.0",

  "model": "mistral/mistral-large-2",
  "model_version": "2402",

  "policy": "policies/default.rego",
  "policy_version": "v1.4.2",
  "policy_result": "ALLOW",
  "policy_rule": null,

  "inputs_hash": "sha256:a3f8c2d19e4b67f0c1a5d8e2b9c3f4a7",
  "output": {
    "decision": "approved",
    "confidence": 0.94
  },

  "override_by": null,
  "override_reason": null,
  "override_at": null,

  "sovereign_scope": "EU",
  "data_residency": "on-premise-de",
  "schema_version": "0.1"
}
```

When a human overrides a policy decision, that override becomes a second
trace entry — linked to the original by `parent_trace_id`, never replacing
it. The audit trail is append-only by design.

```json
{
  "trace_id": "01hx8m2n3p4q5r6s7t8u9v0w1x",
  "parent_trace_id": "01hx7k9m2n3p4q5r6s7t8u9v0w",
  "timestamp": "2026-04-01T14:31:17.891Z",

  "policy_result": "ALLOW",
  "override_by": "ops-lead@example.eu",
  "override_reason": "Manual review completed — approved under delegated authority",
  "override_at": "2026-04-01T14:31:17.891Z",

  "sovereign_scope": "EU",
  "data_residency": "on-premise-de",
  "schema_version": "0.1"
}
```

---

## Architecture

### Today (v0.1)

```
┌─────────────────────────────────────────────────────────────┐
│                    Your AI Agents                            │
│            (any framework, any model, any stack)            │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │     Sentinel Kernel     │
              │                         │
              │  ┌─────────────────┐   │
              │  │   Interceptor   │   │  wraps any agent call
              │  └────────┬────────┘   │
              │           │            │
              │  ┌────────▼────────┐   │
              │  │  Policy Eval    │   │  in-process, no remote call
              │  └────────┬────────┘   │
              │           │            │
              │  ┌────────▼────────┐   │
              │  │ Trace Emission  │   │  structured, tamper-resistant
              │  └────────┬────────┘   │
              │           │            │
              │  ┌────────▼────────┐   │
              │  │    Storage      │   │  your backend, your jurisdiction
              │  └─────────────────┘   │
              └─────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Any model, any provider                         │
│         (the choice is yours — Sentinel records it)          │
└─────────────────────────────────────────────────────────────┘
```

### Evolution path

```
Phase 1 — Kernel (now)
  Interceptor + in-process policy eval + trace emission.
  Any agent framework, any model, any storage backend.

Phase 2 — Storage abstraction (v0.2)
  Formal storage interface with reference implementations.
  Air-gapped export validated in isolated environments.

Phase 3 — Framework integrations (v0.3)
  First-class connectors for major agent orchestration frameworks.
  Zero changes required to existing agent logic.

Phase 4 — BSI reference implementation (v1.0)
  The protocol is formally assessed against BSI IT-Grundschutz.
  Claimed sovereign becomes certified sovereign.
  Unlocks classified government procurement.

Phase 5 — Foundation (v1.0+)
  Protocol governance moves to Linux Foundation Europe.
  No single organisation controls the roadmap.
  The Sentinel specification becomes a standard others implement.
```

---

## Design principles

**1. No US CLOUD Act exposure in the critical path.**
Any service owned by a US-incorporated entity in the trace emission path
creates legal risk for users in regulated European contexts. Sentinel's
critical path contains no such dependency. Optional integrations that
introduce one are clearly labelled.

**2. Air-gapped must always work.**
Local file storage and in-process policy evaluation are the reference
implementation, not a fallback. If a feature cannot be demonstrated in a
network-isolated environment, it is not complete.

**3. The trace is append-only.**
A decision record is permanent. Corrections and overrides are new entries
referencing the original. The original is never modified. This is a legal
requirement for EU AI Act Article 12 compliance.

**4. Policy evaluation is in-process.**
Sentinel evaluates policies synchronously, in the same process as the agent.
No remote call, no network dependency, no single point of failure outside
your control.

**5. Apache 2.0, permanently.**
No licence change, no BSL, no commercial-only features, no relicensing CLA.
This is how trust is established with regulated institutions, government
operators, and the open source community.

---

## How Sentinel differs

The AI governance space is crowded. Understanding where Sentinel fits
requires being clear about what it is not.

| Category | What they do | What Sentinel does |
|---|---|---|
| **Observability** (e.g. LangFuse, LangSmith) | Debug and monitor agent runs | Produce legally-valid sovereign audit records |
| **Content filters** (e.g. NeMo Guardrails, LLM Guard) | Filter inputs and outputs at runtime | Record decisions — does not filter them |
| **Policy engines** (e.g. Open Policy Agent) | Evaluate access policies | Evaluate policies AND record under EU jurisdiction |
| **AI gateways** | Route traffic between model providers | Capture decision context in-process at the agent level |

Sentinel is not better or worse than these tools. It is different in kind.
It answers a different question: not "what did the model say?" but "what was
decided, by whom, under which policy, and under whose law?"

None of the tools above satisfy EU AI Act Article 12 for high-risk AI.
None are designed for classified or air-gapped environments. None produce
tamper-resistant audit trails portable across jurisdictions. Sentinel does.

---

## Integrations

Sentinel wraps any function that makes an AI decision. The pattern is the
same regardless of framework or model.

```python
# Decorate the decision function
@sentinel.trace(policy="policies/your_policy.rego")
async def your_decision_function(input_context):
    # Your existing logic — unchanged
    return await your_agent.run(input_context)
```

For frameworks with middleware or observer hooks, Sentinel provides helpers
that slot in without changes to agent logic. See
[`docs/integration-guide.md`](docs/integration-guide.md).

**Before integrating any framework:**
1. Does it send data to a third-party service at runtime? Document which
   service and its jurisdiction.
2. Does it work in a network-isolated environment? If not, mark as not
   cleared for air-gapped deployment.

Sentinel itself makes no assumptions about which framework or model you use.
Every integration must preserve this property.

---

## Storage

Sentinel writes traces through a single backend-agnostic interface.

```python
class StorageBackend(Protocol):
    async def write(self, trace: DecisionTrace) -> None: ...
    async def get(self, trace_id: str) -> DecisionTrace: ...
    async def query(self, **filters) -> list[DecisionTrace]: ...
    async def export(self, format: str) -> AsyncIterator[str]: ...
```

Four deployment modes are supported:

| Mode | When to use | Sovereignty |
|---|---|---|
| **Local / filesystem** | Development, air-gapped, classified | Full — no network required |
| **On-premise relational** | Enterprise production, regulated industries | Full — you control the infrastructure |
| **On-premise document store** | High-volume deployments | Full — you control the infrastructure |
| **Sovereign edge** | Distributed EU-resident deployments | Full — verify provider jurisdiction |

Bring your own backend by implementing the `StorageBackend` protocol.
One requirement applies to every backend: traces are append-only.
No implementation should support in-place modification of a written trace.

---

## Policy as code

Sentinel evaluates policies synchronously at decision time. The policy
engine is pluggable. The reference implementation uses OPA-compatible Rego,
but any evaluation function returning ALLOW / DENY / EXCEPTION_REQUIRED works.

```rego
# policies/procurement_approval.rego
package sentinel.procurement

default allow = false

allow {
    input.request.value_eur <= input.agent.approval_threshold_eur
}

exception_required {
    input.request.value_eur > 250000
}
```

When a policy returns DENY, Sentinel records which rule triggered.
When a human overrides, that override is a new trace entry.
The complete chain is permanently recorded and queryable.
Policy version is recorded in every trace — any historical decision
can be reconstructed against the exact policy state at that time.

---

## EU AI Act compliance

The EU AI Act (Regulation EU 2024/1689) entered into force 1 August 2024.
For Annex III high-risk AI systems, full compliance is required from
**2 August 2026**. Penalties reach €15 million or 3% of global annual turnover.

| Article | Requirement | How Sentinel addresses it |
|---|---|---|
| **Art. 9** | Risk management system — documented, ongoing | Policy evaluation recorded in every trace; risk posture queryable across all decisions |
| **Art. 12(1)** | Automatic logging of events over the system's lifetime | Every agent decision produces a trace automatically |
| **Art. 12(2)** | Logs must enable identification of risk situations and post-market monitoring | Traces are structured, queryable, exportable |
| **Art. 13** | Transparency — deployers informed about system capabilities | Policy name, version, result recorded in every trace |
| **Art. 14** | Human oversight — effective intervention capability | Override mechanism produces a linked, immutable trace entry |
| **Art. 17** | Quality management — traceability of processes | Continuous tamper-resistant record of system behaviour in production |

**Scoping note.** Whether your AI system is classified as high-risk under
Annex III depends on its specific use case. Sentinel does not make that
classification. Consult legal counsel to determine your obligations.

Full mapping: [`docs/eu-ai-act.md`](docs/eu-ai-act.md)

---

## Deployment

### Local development

```python
sentinel = Sentinel()  # local filesystem, no configuration required
```

### On-premise

```bash
docker run -v /your/data:/data sentinel-kernel/sentinel:latest
```

All traces remain on your infrastructure.

### Air-gapped / classified

```bash
sentinel-cli init --storage filesystem --path /mnt/traces
```

Zero network connectivity required. Policies are bundled with the deployment.
Traces export as NDJSON for offline audit and archival. This is the mode
validated for classified environments and required for VS-NfD deployment.

---

## Roadmap

| Milestone | Target | What it means |
|---|---|---|
| **v0.1 — Kernel** | Q2 2026 | Interceptor, in-process policy eval, and trace emission work. Any agent call can be wrapped and produce a compliant trace. |
| **v0.2 — Storage abstraction** | Q2 2026 | Storage interface formalised. Air-gapped operation validated in network-isolated environments. |
| **v0.3 — Framework integrations** | Q3 2026 | Integration helpers for major agent frameworks. Zero changes required to existing agent logic. |
| **v0.4 — Air-gapped validation** | Q3 2026 | Formal test suite for network-isolated deployment. Reference deployment for classified environments is documented and reproducible. |
| **v1.0 — BSI reference implementation** | Q4 2026 | **The inflection point.** The protocol is assessed against BSI IT-Grundschutz. Claimed sovereign becomes certified sovereign. Unlocks classified government procurement. |
| **v1.1 — VS-NfD deployment profile** | Q1 2027 | Sentinel cleared for VS-NfD classified German government deployments. |

---

## Governance

**License.** Apache 2.0, permanently. Full licence text at
[apache.org/licenses/LICENSE-2.0](https://www.apache.org/licenses/LICENSE-2.0).
No BSL. No commercial-only features. No licence changes. Contributions do not
grant any party the right to relicence this software.

**Foundation.** Sentinel is pursuing stewardship under Linux Foundation Europe.
Application is in progress. Until confirmed, the project is maintained
independently with all governance decisions made transparently through the
RFC process.

**Trademark.** The Sentinel name is intended to be held by the governing
foundation once established, not by any commercial entity.

**Changes.** Significant changes to the trace schema, storage interface,
policy evaluation contract, or sovereignty assertions go through an open RFC
process: a GitHub Discussion is opened, a 14-day comment period follows,
and maintainers vote. The decision and rationale are permanently recorded.

**Funding.** An application to the Sovereign Tech Fund
(Sovereign Tech Fonds) for non-dilutive funding is in progress. No commercial
entity controls the roadmap.

---

## Who is building with Sentinel

Sentinel is in active use by two categories of design partner. Partners are
not named publicly at this stage. What matters is the stakeholder type and
the driving force behind adoption.

**Innovation drivers.** Organisations building AI-enabled hardware and
autonomous systems for regulated markets. They have strong capability at
the sensor, data, and mission layers but need a sovereign decision record
layer to unlock government and defence procurement. US-hosted governance
tools are a structural non-starter for their customer base.

**Sovereign operators.** Government-adjacent IT infrastructure organisations
responsible for deploying technology within classified or sovereign networks.
Their driver: a certified middleware layer they can operate on their own
infrastructure without dependency on external vendors — and which serves as
the deployment channel into broader government systems.

Both categories are shaping the v0.1 → v1.0 protocol. Their production
requirements determine what Sentinel actually needs to handle.

*Your organisation here. Open an issue to discuss design partner status.*

---

## Why sovereignty matters

The AI governance space will consolidate around well-funded platforms.
For most organisations, those platforms are the right choice.

For organisations in defence, critical infrastructure, classified
environments, and European regulated industries, they are not. Not because
of quality — because of jurisdiction.

The US CLOUD Act (18 U.S.C. § 2713) requires US-incorporated companies
to produce data stored anywhere in the world when served with a valid legal
process. This applies to EU subsidiaries of US companies. It applies to EU
data centres operated by US companies. It applies regardless of contractual
commitments. No contract with a US company eliminates CLOUD Act exposure.

EU AI Act Article 12 requires that high-risk AI system logs be technically
tamper-resistant and enable traceability. That requirement has no value if
the logs are accessible to a foreign government under a parallel legal
framework. Sovereignty is not a compliance checkbox. It is the condition
under which compliance is meaningful.

**Sovereign by design. Not sovereign by configuration.**

---

## Contributing

Contributions are welcome from individuals, research institutions,
and organisations.

**First contribution?** Look for issues labelled
[`good first issue`](../../issues?q=label%3A%22good+first+issue%22).

**Adding an integration?** Read [`docs/integration-guide.md`](docs/integration-guide.md)
first. Every integration must document its sovereignty posture.

**Proposing a schema change?** Open an RFC via GitHub Discussions before
writing code. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full RFC process.
