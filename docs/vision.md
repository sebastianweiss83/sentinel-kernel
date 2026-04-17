# Sentinel Vision — Agility Infrastructure for Regulated AI

*Strategic reference. Last updated for v3.3.0. Drawn from the
Sentinel positioning memo (April 2026).*

---

## The situation

In April 2026 the European regulated economy has a structural
problem that has built up over two years and becomes an
existential question in the next eighteen months.

The American AI platforms — OpenAI, Anthropic, Google, Microsoft —
have won the frontier-model layer. That is irreversible. The
Chinese open-weight models — DeepSeek, Qwen, GLM, Kimi — have
broken the cost layer. The cost difference between open-weight
and proprietary APIs sits at ten-to-thirty times. Europe did not
win the model layer and will not. Mistral is real and
significant, but an order of magnitude smaller than Anthropic
and structurally capped. Aleph Alpha has repositioned as an
orchestration stack. European AI investment is a fraction of
American investment.

What Europe has is the regulatory layer. The EU AI Act enters
full force on 2 August 2026. DORA is in force. NIS2 is in force.
BaFin BAIT 8 and MaRisk AT 9 have been substantially tightened.
BSI IT-Grundschutz is binding for critical infrastructure. This
is not a burden. It is the only strategic position Europe
structurally still holds in the AI era, and it will be copied
worldwide the way GDPR was copied.

Between these three realities — American models, Chinese cost,
European regulation — sits the European regulated institution
and does not understand what to do. It pilots. It does not
scale. Every quarter it loses strategic time against greenfield
startups that compete without its constraints. That is not a
tool problem. That is an infrastructure problem.

## How the problem shows up

A platform-engineering lead at a German tier-1 bank put it in
six sentences in April 2026: *"Agents is a huge topic for us,
governance and security included. Feels completely unplannable
— you run a workshop and three new tools have shipped before
it ends. Microsoft and Entra-ID look most promising. Including
Copilot as an agent platform. Everything in motion. We're
starting with small PoCs."*

Six sentences that contain the entire strategic dilemma. The
institution sees the problem, has run the workshops, is
piloting small, and is on the way to adopting Microsoft — not
because Microsoft is the best solution but because it is the
only one that feels as if it would work. The buyer is not
careless; the buyer has no better option.

The same pattern shows up across the top 150 DACH enterprises
in banking, insurance, public-sector IT, defence logistics,
and industrial manufacturing. They see the pattern. They
pilot. They do not scale. They slow down. Greenfield startups
that do not carry the regulatory load win accounts at their
competitors. The accumulated IT landscape turns from an
advantage into a structural disadvantage.

Meanwhile, European startups build modern AI applications —
autonomous systems, defence reconnaissance, precision
industrial — that regulated integrators would like to procure
but cannot, because the compliance cycles are incompatible
with the startups' development speed. In the US this
integration problem is solved by capital. In China it is
solved by state coordination. Europe has neither mechanism.
The integration between European innovation and European
institutional infrastructure does not happen, and that is
why Europe strategically falls behind.

## The reframing

European regulation is read by most decision-makers today as a
blocker. That is wrong. It is the way out.

The EU AI Act forces American and Chinese AI systems deployed
in Europe to demonstrable decision records under EU
jurisdiction. That is not only a compliance burden. It is the
legal grounding on which a European CISO can, for the first
time since the cloud era, say "no" to American standard
platforms — without having to argue against the business case.
*"BAIT 8.2 requires evidence under our jurisdiction"* is not
the burial of an idea. It is the opening of an alternative.

The EU AI Act and its successor regulations convert regulatory
requirements into strategic levers — if the infrastructure
exists to make them operational. *"We satisfy the regulation"*
is defensive. *"We use the regulation to scale faster than our
competitors"* is offensive and commercially stronger.

Regulation, operationalised as infrastructure, makes
established enterprises competitive again against greenfield
startups. Not because the regulation goes away — it does not
go away, it will increase — but because it can be transformed
from process overhead into infrastructure overhead. Process
overhead slows things down. Infrastructure overhead speeds
things up, because every future regulation builds on the same
base instead of being redistributed.

## The central thesis

**Sentinel is the agility infrastructure for regulated European
enterprises, enabling them to move like startups and prove like
banks.**

This thesis has three operative levels that engage in sequence
and build on each other.

**Individual value.** Sentinel is a tool for the single
institution. It lets a regulated enterprise deploy AI systems
faster because the regulatory provability arises automatically
instead of being distributed across processes. The six-week
compliance review every bank knows becomes a three-day routine
check. The PoC that otherwise dies in pilot scales to
production.

**Ecosystem value.** Sentinel is a bridge in mixed ecosystems.
When an established integrator and a fast-moving startup must
work on the same system, Sentinel sits between them. The
startup develops quickly; Sentinel records every decision in a
format the integrator's compliance processes accept. The
integrator does not need to match the startup's pace. The
startup does not need to learn the integrator's bureaucracy.
The infrastructure layer mediates.

**Structural value.** Sentinel is Europe's technical answer to
the integration problem the US solves through capital and
China solves through power. Europe has neither the capital for
acquisition-driven consolidation nor the political structure
for mandated integration. So it must happen through
infrastructure — through a common language for AI decisions
that both fast-moving startups and established institutions
can speak.

These three levels are not three products. They are three
zoom levels of the same thing. The infrastructure that
delivers level one is exactly the infrastructure that enables
level two, which is exactly the infrastructure that carries
level three.

## Record. Enforce. Prove.

Three verbs. Each a clearly defined operation. Together the
complete lifecycle of an AI decision in a regulated
environment.

**Record.** Every AI decision is recorded with context,
input hash, timestamp, and outcome. Append-only, tamper-
resistant, privacy-by-default (SHA-256 hash instead of raw
input, unless explicitly configured), stored under the
operator's jurisdiction. Sentinel's `@sentinel.trace`
decorator delivers this today. Apache 2.0. One-line install.

```python
from sentinel import Sentinel

sentinel = Sentinel()                       # local storage, zero config

@sentinel.trace
async def approve(request: dict) -> dict:
    return await your_agent.run(request)    # unchanged

await approve({"amount": 50_000})
# → DecisionTrace persisted: data_residency=local,
#   inputs_hash=sha256:..., policy_result=ALLOW
```

**Enforce.** Every AI decision passes through a policy layer
before it executes. Policy-as-Code — OPA/Rego or Python.
Versioned, testable, CI/CD-deployable. The EU AI Act Art. 14
kill-switch primitive is first-class. Multi-party approval
gates are available. Sentinel implements this today.

**Prove.** Every record, every policy decision can be
aggregated into an evidence pack — cryptographically signed,
mapped to EU AI Act, DORA, NIS2, and BSI IT-Grundschutz, in a
format an auditor accepts. The basic generator is open source.
Enterprise features (HSM signing, RFC-3161 timestamping via
EU TSAs, long-term retention of ten-plus years, automated
BaFin reporting templates, legal-hold management) are
commercial.

This formula is distinctive. Dome Systems uses "Connect.
Secure. Operate." as its agent-governance lifecycle. That is
good but general — it could apply to IoT or classical
microservices equally. *Record. Enforce. Prove.* is specific to
the AI-decision context and leads directly to the evidence
artefact European regulation requires.

## The four modules

Sentinel is one product with four functional modules. The
modules share a single codebase, a single data model, a single
CLI, and a single installation. They are not four products.
They are four faces of the same product, each serving a
different buyer archetype.

```
Your business logic
        │
        ▼
┌─────────────────────────────────────────┐
│              SENTINEL                   │
│   Agility infrastructure for AI         │
│                                         │
│  ┌────────┐ ┌────────┐ ┌────────┐       │
│  │ TRACE  │ │ POLICY │ │EVIDENCE│       │
│  │   ✓    │ │   ✓    │ │   ✓    │       │
│  │ Record │ │Enforce │ │  Prove │       │
│  └────────┘ └────────┘ └────────┘       │
│                                         │
│  ┌───────────────────────────────┐      │
│  │       FEDERATION → roadmap    │      │
│  │   Multi-institution aggregate │      │
│  └───────────────────────────────┘      │
└─────────────────────────────────────────┘
        │
        ▼
  DECISION LAYER (your choice)
  LLMs · ML classifiers · Rule engines · Robotic systems
  Switch anytime. No lock-in.
        │
        ▼
  LOCAL STORAGE (your infrastructure)
  SQLite · PostgreSQL · NDJSON
```

**Sentinel Trace** is the entry point for developers. The
`@sentinel.trace` decorator, install via `python3 -m pip
install --user sentinel-kernel`, value in five minutes: the
developer sees what their AI agent decided, with which inputs,
under which policy evaluation, in what time. This module stays
Apache 2.0 permanently. It is the distribution flywheel. The
developer does not pay, but they carry Sentinel into their
team, and the team into the organisation.

**Sentinel Policy** is the entry point for platform-
engineering teams. OPA/Rego-based or Python-rule-based policy
enforcement on every traced call. The base engine stays Apache
2.0. Commercial are preconfigured industry policy libraries —
BaFin catalogues, KRITIS rulebooks, defence use-case templates,
EU AI Act Art. 5 prohibition lists. The value is consistency
across models and systems. Deploying a new AI system does not
mean "new compliance processes" but "apply existing policies."

**Sentinel Evidence** is the entry point for CISOs, DPOs,
compliance officers, and internal audit. Evidence packs as
PDF and NDJSON, cryptographically signed, mapped to EU AI Act,
DORA, NIS2, BSI IT-Grundschutz. The default generator stays
Apache 2.0. Commercial enterprise features are HSM integration,
RFC-3161 timestamping via EU timestamping authorities, multi-
party signing for critical decisions, long-term retention of
ten-plus years (BaFin retention obligation), automated BaFin
reporting templates, legal-hold management.

**Sentinel Federation** is the entry point for multi-
institution scenarios: holding-group structures, industry
consortia, supervisory oversight. This is the future module,
not shipping today but architecturally anchored and publicly
committed as roadmap. It will enable aggregated compliance
visibility across federated institutions without individual
data disclosure. Relevance: holding-company subsidiaries,
supervisory oversight over banking groups, KRITIS sector
coordination, the bridge between fast movers and slow
institutions at larger scale.

The modules are not invented by marketing. They correspond
exactly to the structure that already exists in the code:
`sentinel/core/` has the tracer and storage backends;
`sentinel/policy/` has the evaluator with OPA integration;
`sentinel/compliance/` has the checkers for EU AI Act, DORA,
NIS2, BSI, plus the evidence-pack generator; `sentinel/core/
attestation.py` has the signing infrastructure;
`sentinel/federation/` exists as a roadmap placeholder with a
defined interface.

### Note on the refinement from "Three-Layer" to "Four-Module"

Sentinel has always been four things. Until v3.2 we described
the first three as a two-and-a-half-layer kernel (Trace +
Govern, with Evidence bundled under Govern) and used Route /
SovereignRouter as a placeholder for the fourth layer. From
v3.3 onward we use four explicit names. Evidence stands alone
because it is what regulated buyers pay for. Federation
replaces Route as the roadmap slot because multi-institution
aggregation is the larger strategic question; routing between
models is a narrower capability that may re-emerge as a
Federation sub-feature, not an independent layer.

## What Sentinel is not

Errors in positioning arise from scope creep, not from
under-positioning.

Sentinel is not an AI platform. Sentinel hosts no models,
calls no LLMs, runs no inference. Sentinel is the layer that
records, enforces, and proves the decisions of other AI
systems.

Sentinel is not a complete compliance solution. EU AI Act
compliance spans Articles 9 through 17 and more. Sentinel
primarily addresses Articles 12, 13, and 14, and partially 9,
11, 16, 17, 26, and 72. The rest organisations must cover
themselves or with other tools. This honesty builds trust;
the alternative (overclaiming) loses it.

Sentinel is not an observability tool. LangFuse, LangSmith,
Weights & Biases do observability. Sentinel tracks decisions
and policies. Complementary.

Sentinel is not a security platform. NeMo Guardrails, LLM
Guard, garak filter prompts and detect jailbreaks. Sentinel
comes after the security layer: what did the system that
passed security decide, and is the resulting artefact
provable.

Sentinel will not pursue a closed-source strategy. The kernel
stays Apache 2.0 permanently. Enterprise features are always
add-ons to a permanently open core. This commitment is not
negotiable — it guarantees the BaFin BAIT 8.2 exit capability
regulated buyers require.

Sentinel will never be US-incorporated. The company stays
Swentures UG under German jurisdiction. An American
subsidiary for US market access can exist later, but the core
entity and the evidence infrastructure stay EU-incorporated.

## The competitive landscape

**Dome Systems** — US-incorporated, closed beta, building an
agentic infrastructure platform with significant venture
backing. Intellectually strong positioning through three
essays. Dome will take the US market and western Fortune-500.
Sentinel does not compete directly with Dome; the markets are
geographically and jurisdictionally separated. Dome cannot
effectively serve regulated European institutions because any
US-incorporated entity falls under the CLOUD Act (18 U.S.C.
§ 2713), regardless of data-centre location. BaFin BAIT 8.2
exit capability is not credibly demonstrable under closed
SaaS, even with escrow.

**Microsoft Agent Governance Toolkit (AGT).** US-incorporated,
MIT-licensed. Covers OWASP Agentic Top 10, framework-agnostic
with LangChain/CrewAI/Dify integration. Microsoft AGT wins
every Microsoft-shop without a sales call. Sentinel is not a
direct competitor in Microsoft-first shops without an
explicit EU-jurisdiction requirement. Sentinel is the answer
for enterprises that must work model-agnostically or must
hold evidence artefacts explicitly under EU jurisdiction.
This is often a co-existence in the reality of European
banking, not a replacement.

**Cylake.** US-incorporated, founded by Nir Zuk (Palo Alto
Networks). "Sovereignty is the next firewall." Targets nation
states and tier-1 banks with hardware + software. Cylake is
not a direct competitor but is currently claiming the word
*Sovereignty* in the cybersecurity context with billions of
marketing weight. The semantic shadow is real. That is why
Sentinel does not lead with Sovereignty — it leads with
*Provability*, operationalised as *Record. Enforce. Prove.*,
with Sovereignty as a consequence rather than a thesis.

**Native cloud governance — Azure AI Foundry, AWS Bedrock
Guardrails, GCP Vertex AI.** Deeply integrated. Excellent
when an organisation stays on one cloud. Loses value the
moment multi-cloud or on-premise scenarios appear. Sentinel
is the multi-cloud-plus-on-premise clasp.

**Native AI-provider governance.** Anthropic, OpenAI, Google
will build proprietary governance features into their models.
These will work excellently — per model. They will not be
structurally model-spanning, because that contradicts their
business model. They will also not be under EU jurisdiction,
because the firms are US-incorporated. Sentinel sits one
layer above and abstracts.

**LangFuse, LangSmith, Weights & Biases.** Observability.
Measure performance, tokens, latency. Complementary, not
competing. LangFuse ships a Sentinel-compatible integration.

**Sastrify, Enactia, Kovrr, ADOGRC — GRC platforms.** Not
competitors. Partner candidates. They operate on the
inventory-and-management layer. Sentinel operates on the
runtime layer. The layers complement each other.

The gap in this landscape is observable. No other solution
simultaneously offers: model-spanning consistency, EU
jurisdiction for evidence, open source with exit capability,
cryptographic provability in regulation-mapped format.
Sentinel positions precisely in this intersection.

## The market timing

Three independent clocks align in 2026.

**The regulator.** EU AI Act Annex III high-risk enforcement
begins 2 August 2026. Penalties up to €15M or 3% of global
annual turnover. Every regulated European buyer must
demonstrate automatic tamper-resistant decision logging from
that date. The procurement conversations for Q4 2026 are
happening now.

**The sovereignty moment.** After two years of CLOUD Act
headlines and Schrems-era jurisprudence, *"EU-jurisdictional"*
has stopped being marketing and started being a purchase
criterion. BSI publishes reference profiles. Linux Foundation
Europe exists specifically to give open-source projects an
EU-governed home. The infrastructure to be credibly operated
under EU jurisdiction exists for the first time.

**The empty field.** Nobody is building this exact thing.
Large US observability tools are observability tools, tied to
LLMs. Cloud providers are cloud providers. The EU-operated
projects we respect — Mistral, Aleph Alpha, Haystack,
Nextcloud — are model vendors, orchestration stacks, or
collaboration platforms, not decision infrastructure.
Sentinel is the only open-source, EU-operated, technology-
agnostic decision infrastructure we can find. That will not
last forever. It should last long enough to become the
default.

## Realistic scope

Sentinel will not be Mistral. Sentinel will not be Anthropic.
Sentinel will not be HashiCorp in the pre-IBM era. Those
scales require venture capital in US or Chinese ecosystems
and conditions Europe structurally does not offer.

What Sentinel can realistically become, at a good outcome
over five-to-seven years: a category that must exist because
regulation forces it to, occupied by an EU-incorporated
vendor because US competitors structurally cannot occupy it.

This is not "change the world." It is "occupy a structural
position in Europe that a US competitor would otherwise take,
and give Europe an option it otherwise would not have." That
is an honest, realistic, achievable ambition. It is smaller
than the maximum formulated in session-high moments. It is
bigger than most European infrastructure firms have ever
managed.

## The bottom line

Scale what you can prove. Move like a startup. Prove like a
regulated bank.

The rest is implementation.

---

*Full competitive detail: [docs/landscape.md](landscape.md) ·
Phase plan: [docs/roadmap.md](roadmap.md) · Provability
conditions: [docs/provability.md](provability.md) ·
What Sentinel is not, extended: [docs/commercial.md](commercial.md).*
