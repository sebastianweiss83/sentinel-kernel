# Sentinel Vision — The Sovereign Decision Kernel

Sentinel is not compliance middleware. Sentinel is the **Sovereign Decision
Kernel** — a thin, open-source, EU-sovereign layer that sits between your
business logic and any autonomous decision system, and answers four questions
every regulated enterprise has to answer in 2026.

## The problem

Every CIO and every BSI auditor now has four questions about autonomous
systems in production:

1. **What did the system decide, and can we prove it later?**
   EU AI Act Art. 12 and Art. 17 require automatic, tamper-resistant decision
   records from 2 August 2026. A screenshot in Slack will not do.

2. **What is the system allowed to decide in the first place?**
   Policy cannot live in a Word document. It must be machine-checked at the
   moment of the decision, and the result must be provable later. Art. 14
   (human oversight) requires a working kill switch, not a meeting.

3. **Which system made that decision, and is it even legal for this
   data class?**
   A classified procurement decision cannot be sent to an API in Oregon.
   "Which system" is itself a compliance question — one that grows more
   urgent every month as the technology landscape fragments.

4. **Does this work for our ML pipeline, not just our LLM?**
   Yes. Sentinel traces decisions, not models. The `@sentinel.trace`
   decorator wraps any Python function — LLM calls, ML classifiers,
   rule engines, robotic control systems. If it decides, Sentinel records it.

Most products on the market answer exactly one of these questions. Sentinel
answers all four, in one thin kernel that you can read end-to-end.

## The three-layer architecture

```
Your business logic
        │
        ▼
┌──────────────────────────────────────────┐
│           SENTINEL KERNEL                │
│                                          │
│  ┌───────────────┐  ┌──────────────────┐ │
│  │   GOVERN ✓    │  │    ROUTE → v4.0  │ │
│  │  policy-code  │  │   which model?   │ │
│  │  kill switch  │  │   sovereignty?   │ │
│  │  preflight    │  │   data class?    │ │
│  └───────────────┘  └──────────────────┘ │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │           TRACE ✓                │    │
│  │  sovereign · tamper-resistant    │    │
│  └──────────────────────────────────┘    │
└──────────────────────────────────────────┘
        │
        ▼
   DECISION LAYER (your choice)
   LLMs · ML classifiers · Rule engines · Robotic systems
        │
        ▼
   SOVEREIGN STORAGE
   SQLite · PostgreSQL · NDJSON
```

### Layer 1 — Trace (v3.0, shipped)

Every autonomous decision becomes a structured, append-only, sovereign record. SHA-256
hashed inputs. UTC timestamps. Policy result. Model used. Sovereignty scope.
Data residency. Art. 12 compliance is an automated side-effect of the
interceptor, not a project.

```python
from sentinel import Sentinel

sentinel = Sentinel()                       # local storage, zero config

@sentinel.trace
async def approve(request: dict) -> dict:
    return await your_agent.run(request)    # unchanged

await approve({"amount": 50_000})
# → DecisionTrace persisted: sovereign_scope=EU, data_residency=local,
#   inputs_hash=sha256:..., policy_result=ALLOW
```

Optional ML-DSA-65 (FIPS 204, BSI TR-02102-1) signing keeps the records
tamper-resistant against a quantum-era adversary, with keys that never leave
your infrastructure.

### Layer 2 — Govern (v3.0, shipped)

What the system is allowed to decide is policy-as-code, evaluated in-process,
recorded in every trace. The kill switch (Art. 14) halts every wrapped call
instantly without a restart. The manifesto declares which dependencies,
models, jurisdictions, and data classes are acceptable — and runs as five
named CI theses on every pull request.

```python
from sentinel import Sentinel
from sentinel.manifesto import SentinelManifesto
from sentinel.manifesto.requirements import EUOnly, Required, AcknowledgedGap

class OurPolicy(SentinelManifesto):
    name = "Production Sovereignty Policy v1"
    jurisdiction = EUOnly()
    kill_switch = Required()
    ci_cd = AcknowledgedGap(
        provider="GitHub Actions (Microsoft/US)",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
    )

sentinel = Sentinel()
report = OurPolicy().check(sentinel_instance=sentinel)
print(f"Score: {report.overall_score:.0%}")
```

Govern is not an afterthought layer bolted on top of Trace. It is evaluated
by the same kernel, in the same interceptor, and recorded in the same
DecisionTrace. There is no way for a policy to fail silently.

### Layer 3 — Route (v4.0, roadmap)

Layer 3 answers the last, and hardest, question: **which system should even
handle this decision?**

The same SentinelManifesto that defines what may be decided defines which
systems are acceptable for each data class. The router reuses the existing
policy engine, selects the right decision system, records the choice and the
reason as part of the sovereign trace, and falls back automatically if the
preferred system is unavailable.

```python
# Layer 3 — Route (v4.0 vision)
result = await sentinel.route(
    task="classify_document",
    context={
        "classification": "VS-NfD",
        "content": document,
    },
)
# Sentinel decides, based on manifesto:
#   classification "VS-NfD" → requires air-gapped model
#   → uses llama3-70b-local, not claude-api
#   → records: model chosen, why, sovereignty proof, decision trace
print(result.model_used)         # "llama3-70b-local"
print(result.reason)             # "VS-NfD requires air-gapped model"
print(result.sovereignty_proof)  # attestation hash
```

Route is what turns "we use Sentinel for logging" into "we use Sentinel as
our decision platform." It is also what breaks vendor lock-in: the choice
of decision system becomes a configuration of your manifesto, not a rewrite
of your code.

## Why the technology doesn't matter

The EU AI Act Art. 12 requirement is technology-neutral. It requires
automatic, tamper-resistant logging of every decision made by a high-risk
AI system. The regulation does not define "AI system" as "large language
model." It defines it as any system that influences decisions affecting
people's rights, safety, or access to services.

That includes:
- LLMs making procurement approvals
- ML classifiers making credit decisions
- Rule engines making insurance eligibility decisions
- Autonomous systems making operational decisions
- Robotic systems making physical action decisions

Sentinel wraps any Python function that makes such a decision. The
`@sentinel.trace` decorator is technology-neutral by design.

This means Sentinel is sustainable beyond any single technology wave.
LLMs are the current dominant paradigm. They will not be the last. The
regulatory obligation to produce a sovereign decision record will outlast
every specific technology.

## Why not Palantir AIP

Palantir AIP is an excellent product. It is also, structurally, the wrong
answer for regulated European buyers, for three reasons that are architectural
rather than tactical.

**Jurisdiction.** Palantir is US-incorporated. The US CLOUD Act (18 U.S.C.
§ 2713) applies to all data it handles, regardless of where the servers are.
No EU data-centre agreement, no contractual clause, eliminates this. For a
defence contractor, a Landesbank, or a Bundesbehörde, that is a structural
barrier, not a preference.

**Cost and lock-in.** AIP engagements start at €5–20M per year and require
deployment strategists — Palantir's own consultants — to integrate it with
your business. The ontology, the pipelines, and the UI are proprietary. When
you want to leave, you have to rebuild everything.

**The shape of the next decade.** When LLMs guide their own integration — and
that is already happening — the deployment-strategist model collapses. A good
agent with a good manifesto and a good kernel can wire up the pipelines by
itself. What survives is the trusted kernel underneath: policy, audit trail,
model router, sovereignty proof. That is Sentinel. Open source, EU sovereign,
Apache 2.0, self-service.

| Solution | Jurisdiction  | Open       | System-agnostic | Air-gapped | Router      |
|----------|---------------|------------|-----------------|-----------|-------------|
| Palantir AIP | US CLOUD Act | ✗         | Partial         | ✗          | Proprietary |
| LangSmith    | US CLOUD Act | ✗         | LLMs only       | ✗          | ✗           |
| asqav-sdk    | US cloud     | MIT        | ✗               | ✗          | ✗           |
| **Sentinel** | **EU**       | **Apache 2.0** | **✓ any system** | **✓**  | **→ v4.0**  |

| Non-LLM capability           | Cloud obs. | Proprietary | Sentinel |
|-------------------------------|-----------|-------------|----------|
| ML classifier governance      | ✗         | ✗           | ✓        |
| Rule engine audit trail        | ✗         | ✗           | ✓        |
| Robotic decision logging       | ✗         | ✗           | ✓        |

## The market timing

Three independent clocks line up in 2026.

**The EU AI Act.** Annex III high-risk enforcement begins 2 August 2026.
Every European bank, insurer, critical-infrastructure operator, healthcare
provider, defence contractor, and government agency has to demonstrate
automatic tamper-resistant decision logging from that date, under penalty
of up to €15M or 3% of global turnover. The procurement conversations for
Q4 2026 are happening now.

**The sovereignty moment.** After two years of CLOUD Act headlines and
Schrems-era jurisprudence, "EU-sovereign" has stopped being marketing and
started being a purchase criterion. Bundesamt für Sicherheit in der
Informationstechnik (BSI) has published reference profiles. Linux
Foundation Europe exists specifically to give open-source projects an
EU-governed home. The infrastructure to be credibly sovereign exists for
the first time.

**The empty field.** Nobody is building this exact thing. The big US
observability tools are observability tools — tied to LLMs. The cloud
providers are cloud providers. The EU-sovereign projects we respect —
Mistral, Mittagessen, Nextcloud — are model vendors or collaboration
platforms, not decision kernels. Sentinel is the only open-source,
EU-sovereign, technology-agnostic decision kernel we can find. That will
not last forever. It should last long enough to become the default.

## Roadmap

**Phase 1 — Trace + Govern (v1.0–v3.1, shipped).**
Sovereign decision traces, policy-as-code, kill switch, manifesto-as-code,
EU AI Act compliance checker, sovereignty scanner, quantum-safe signing,
RFC-001 cross-language manifest. v3.0 froze the public API. v3.1 — The
Auditor Release — added `sentinel ci-check`, `sentinel evidence-pack`
(signed PDF evidence packs), and honest-scope framing across all
surfaces. Production stable. 686 tests. 100% line and branch coverage
enforced in CI.

**Phase 2 — Certify (v3.2, 2026).**
Linux Foundation Europe stewardship application and BSI IT-Grundschutz
formal assessment, both targeted for v3.2 in Q3/Q4 2026. First
lighthouse deployments. Go and TypeScript reference implementations
of RFC-001.

**Phase 3 — Route (v4.0–v4.x, 2026–2027).**
SovereignRouter. Policy-driven model selection. Local model adapters
(Ollama, vLLM, llama.cpp). Multi-model consensus for high-stakes decisions.
LLM-guided deployment — the kernel wires itself into new environments.

**Phase 4 — Ecosystem (v5.x, 2027+).**
EU-sovereign build pipeline (Gitea/Forgejo instead of GitHub Actions). EU
package registry (instead of PyPI). Signed build artifacts end-to-end.
Multi-language parity.

## The bottom line

Sentinel is a thin, open, auditable kernel. You can read every line of it.
You can run it air-gapped. You can swap the model layer without rewriting
your business logic. You can hand the whole thing to a BSI auditor without
a single proprietary black box in the critical path. And when v4.0 ships,
the same kernel that recorded your decisions will also decide which model
makes them — under the same manifesto, with the same sovereignty guarantees,
with no vendor in the loop. That is the product. The rest is implementation.
