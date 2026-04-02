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

---

## The landscape and where Sentinel sits

Three categories of tooling are converging on the agent governance problem.
Understanding the distinction matters.

**AI Ops** — observability, tracing, evaluation. Tools that help you understand
what your agents did after the fact. Excellent for debugging and performance
monitoring. Not designed for legal compliance. Not sovereign. Not tamper-resistant.

**Policy management and runtime enforcement** — tools that evaluate rules at
inference time and block or permit actions. Useful for content safety and access
control. They answer "should this action be allowed?" Sentinel answers "what was
decided, and can you prove it before a regulator?" These are complementary,
not competing.

**Decision record infrastructure** — this is what Sentinel is. The layer that
produces a legally-valid, tamper-resistant, sovereign artifact for every AI
decision. It does not exist as an open, jurisdiction-neutral standard yet.
That is the gap.

The crowded space is real. None of it is designed for classified environments,
air-gapped networks, or EU legal jurisdiction.

**On the ecosystem play.** The leading proprietary platform in this space is
actively building a developer ecosystem: SDKs, community app registries,
framework connectors. Every component of that ecosystem deepens the same
lock-in. Developers who build agent workflows on that platform build against a
proprietary ontology, a proprietary SDK, and a US-jurisdicted runtime. The
community registry they curate is growing. The flywheel is real.

Sentinel's answer is not to compete for the same developers in the same market.
It is to be the open, sovereign alternative for the developers and organisations
that the proprietary platform structurally cannot serve — those in classified
environments, sovereign procurement, and regulated EU industries. For those
organisations, an open LangChain connector to a sovereign decision record layer
is not a feature. It is the only viable option.

**On standardisation.** General-purpose middleware typically needs a hyperscaler
or major lab to drive protocol adoption. Sentinel operates in a different
dynamic. BSI IT-Grundschutz certification creates a mandatory adoption mechanism
in regulated German and EU defence markets — not by preference, but by
procurement law. The design partners shaping the v0.1 → v1.0 protocol are the
same organisations that will be required to comply with it. That is the flywheel.

Linux Foundation Europe provides the neutral governance home that makes this
credible to regulators, procurement committees, and contributors who will not
adopt a protocol controlled by a single commercial entity.

---

## Five-minute quick start

```bash
pip install sentinel-kernel
```

```python
from sentinel import Sentinel

# Local storage by default — no cloud account, no network required
sentinel = Sentinel()

@sentinel.trace(policy="policies/default.rego")
async def evaluate_request(context: dict) -> dict:
    # Your existing agent logic — completely unchanged
    result = await your_model.call(context)
    return result

outcome = await evaluate_request({"action": "approve", "amount": 50000})
```

Every call now produces a decision trace. Written to local storage.
Exportable as NDJSON. Satisfies EU AI Act Article 12 out of the box.

**Time to first trace: under five minutes.**

---

## Example trace output

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
  "output": { "decision": "approved", "confidence": 0.94 },

  "override_by": null,
  "override_reason": null,
  "override_at": null,

  "sovereign_scope": "EU",
  "data_residency": "on-premise-de",
  "schema_version": "0.1"
}
```

When a human overrides a policy decision, that override becomes a second
trace entry — linked to the original by `parent_trace_id`, never replacing it.
The audit trail is append-only by design.

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
  Formal storage interface. Reference implementations.
  Air-gapped export validated in isolated environments.

Phase 3 — Framework integrations (v0.3)
  First-class connectors for major agent orchestration frameworks,
  including LangChain — the open, sovereign alternative to
  proprietary platform connectors.
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
No remote call, no network dependency, no external single point of failure.

**5. Apache 2.0, permanently.**
No licence change, no BSL, no commercial-only features, no relicensing CLA.
This is how trust is established with regulated institutions, government
operators, and the open source community.

---

## How Sentinel differs

| Category | What they do | What Sentinel does |
|---|---|---|
| **Observability** | Debug and monitor agent runs | Produce legally-valid sovereign audit records |
| **Content filters** | Filter inputs and outputs at runtime | Record decisions — does not filter them |
| **Policy engines** | Evaluate access policies | Evaluate policies AND record under EU jurisdiction |
| **Proprietary platforms** | Capture decisions inside a vendor ecosystem | Record decisions in an open, portable, sovereign format you control |

Sentinel is not better or worse than these tools. It is different in kind.
It answers a different question: not "what did the model say?" but "what was
decided, by whom, under which policy, and under whose law?"

None of the categories above satisfy EU AI Act Article 12 for high-risk AI.
None are designed for classified or air-gapped environments. None produce
tamper-resistant audit trails portable across jurisdictions. Sentinel does.

---

## Integrations

Sentinel wraps any function that makes an AI decision. The pattern is the
same regardless of framework or model.

```python
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

| Mode | When to use | Sovereignty |
|---|---|---|
| **Local / filesystem** | Development, air-gapped, classified | Full — no network required |
| **On-premise relational** | Enterprise production, regulated industries | Full — you control the infrastructure |
| **On-premise document store** | High-volume deployments | Full — you control the infrastructure |
| **Sovereign edge** | Distributed EU-resident deployments | Full — verify provider jurisdiction |

Bring your own backend by implementing the `StorageBackend` protocol.
One requirement applies universally: traces are append-only. No backend
should support in-place modification of a written trace.

---

## Policy as code

Sentinel evaluates policies synchronously at decision time. The policy engine
is pluggable. The reference implementation uses OPA-compatible Rego, but any
evaluation function returning ALLOW / DENY / EXCEPTION_REQUIRED works.

```rego
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
Policy version is recorded in every trace — any historical decision
can be reconstructed against the exact policy state at that time.

---

## EU AI Act compliance

The EU AI Act (Regulation EU 2024/1689) entered into force 1 August 2024.
For Annex III high-risk AI systems, full compliance is required from
**2 August 2026**. Penalties reach €15 million or 3% of global annual turnover.

| Article | Requirement | How Sentinel addresses it |
|---|---|---|
| **Art. 9** | Risk management — documented, ongoing | Policy evaluation recorded in every trace; risk posture queryable |
| **Art. 12(1)** | Automatic logging over the system's lifetime | Every decision produces a trace automatically — no manual step |
| **Art. 12(2)** | Logs enable identification of risk situations | Traces are structured, queryable, exportable |
| **Art. 13** | Transparency to deployers | Policy name, version, result recorded in every trace |
| **Art. 14** | Human oversight — effective intervention | Override mechanism produces a linked, immutable trace entry |
| **Art. 17** | Quality management — traceability | Continuous tamper-resistant record of system behaviour |

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

### Air-gapped / classified

```bash
sentinel-cli init --storage filesystem --path /mnt/traces
```

Zero network connectivity required. Policies bundled with the deployment.
Traces export as NDJSON. The reference mode for classified environments
and VS-NfD deployment profiles.

---

## Roadmap

| Milestone | Target | What it means |
|---|---|---|
| **v0.1 — Kernel** | Q2 2026 | Interceptor, in-process policy eval, trace emission. Any agent call can be wrapped and produce a compliant trace. |
| **v0.2 — Storage abstraction** | Q2 2026 | Storage interface formalised. Air-gapped operation validated in network-isolated environments. |
| **v0.3 — Framework integrations** | Q3 2026 | Integration helpers for major agent frameworks including LangChain — open, sovereign, portable. Zero changes to existing agent logic. |
| **v0.4 — Air-gapped validation** | Q3 2026 | Formal test suite for network-isolated deployment. Reference deployment for classified environments documented and reproducible. |
| **v1.0 — BSI reference implementation** | Q4 2026 | **The inflection point.** Protocol assessed against BSI IT-Grundschutz. Claimed sovereign becomes certified sovereign. Unlocks classified government procurement. |
| **v1.1 — VS-NfD deployment profile** | Q1 2027 | Sentinel cleared for VS-NfD classified German government deployments. |

---

## Governance

**License.** Apache 2.0, permanently. Full text at
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

**Funding.** An application to the Sovereign Tech Fund for non-dilutive
funding is in progress. No commercial entity controls the roadmap.

---

## Who is building with Sentinel

Sentinel is in active use by two categories of design partner. Partners are
not named publicly at this stage.

**Innovation drivers.** Organisations building AI-enabled hardware and
autonomous systems for regulated markets. They have strong capability at
the sensor, data, and mission layers but need a sovereign decision record
layer to unlock government and defence procurement. Proprietary US-hosted
governance tools are a structural non-starter for their customer base.

**Sovereign operators.** Government-adjacent IT infrastructure organisations
responsible for deploying technology within classified or sovereign networks.
Their driver: a certified middleware layer they can operate on their own
infrastructure without dependency on external vendors — and which serves as
the deployment channel into broader government systems.

Both categories are shaping the v0.1 → v1.0 protocol. Their production
requirements determine what Sentinel needs to handle.

*Your organisation here. Open an issue to discuss design partner status.*

---

## Why sovereignty matters

The AI governance space will consolidate around well-funded, proprietary
platforms. For most organisations, those platforms are the right choice.

For organisations in defence, critical infrastructure, classified environments,
and European regulated industries, they are not. Not because of quality —
because of jurisdiction.

The US CLOUD Act (18 U.S.C. § 2713) requires US-incorporated companies to
produce data stored anywhere in the world when served with a valid legal
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
writing code. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
