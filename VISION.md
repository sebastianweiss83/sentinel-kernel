# Vision

**Sentinel's vision is to become the open standard for AI decision infrastructure in Europe** — the layer that makes AI agents auditable, sovereign, and trustworthy by design.

---

## The problem

Every AI agent your organisation runs makes decisions. Approves a discount. Routes an escalation. Denies a loan. Grants an exception. Flags a transaction.

Those decisions are currently invisible.

Not because the technology to capture them doesn't exist — it does. But because the dominant AI platforms are built by companies whose business model is data accumulation and vendor lock-in. When a proprietary platform captures your decision traces inside its system of record, the asset that forms — the institutional memory of how your organisation actually makes decisions — belongs to a foreign platform.

For European enterprises in regulated industries, this is not a preference problem. It is a structural one.

GDPR. The EU AI Act (Article 12: automatic logging for high-risk AI systems, effective August 2026). DORA for financial services. NIS2 for critical infrastructure. These regulations collectively establish that European enterprises must control their AI decision lineage — who approved what, under which policy, with which model, with data staying where.

No US-headquartered platform can guarantee this. Not architecturally. Not legally. Not in a world where the CLOUD Act can compel disclosure of data held by US-headquartered companies operating in Europe.

**Sentinel exists to fill this gap.** Not as a European competitor trying to out-resource the incumbents. But as open source infrastructure — owned by no company, governed by a foundation, auditable by anyone — that any European enterprise, research institution, or government can deploy, extend, and trust.

---

## What we believe

**Decision traces are the next system of record.**

The last generation of enterprise software created trillion-dollar platforms by owning canonical data: customer records, operational records, employee records. The next generation will be built by whoever owns decision records — the "why" layer that explains not just what the data shows, but what was decided, by whom, under which policy, and what set the precedent for next time.

We call this the sovereign decision layer — and we believe it must be open.

**Sovereignty is not a feature, it is the architecture.**

You cannot bolt sovereignty onto an existing system. You cannot call a US-hosted SaaS API and claim data sovereignty because the response comes back to your servers. Sovereignty means the decision trace — the full context of what was decided and why — never leaves infrastructure you control. It is captured locally, stored locally, and remains yours. This requires a different architecture from the ground up, not a compliance wrapper around an existing one.

**Open source is the only governance model Europeans will trust.**

A closed-source sovereign AI middleware is a contradiction in terms. "Trust us, it's sovereign" is not an auditable claim. An open source kernel, governed by a foundation with a permanent Apache 2.0 licence and a public RFC process, is. Regulators can inspect it. Security researchers can audit it. Enterprises can fork it. No single company can change its licence, deprecate its API, or introduce a backdoor without the community seeing.

**The standard should be written by practitioners, not regulators.**

The EU AI Act defines what must be logged. It does not define how. The BSI will eventually publish a profile for sovereign AI middleware. It does not exist yet. The organisations that ship real deployments first — in production, in classified environments, in regulated industries — will write the reference implementation that regulators point at. We intend to be those organisations. Every production deployment shapes the standard.

**Small is powerful.**

The infrastructure projects that become standards — Linux, Kubernetes, OpenTelemetry — succeeded not because they were the largest, but because they were the minimum viable thing that solved the problem precisely, and let everyone build on top. Sentinel is the kernel. The ecosystem builds around it.

---

## What we are building toward

### By end of 2026

A production-ready open source kernel that:
- Captures structured decision traces from any AI agent framework
- Evaluates OPA-compatible policies at decision time
- Deploys sovereign: on-premise, air-gapped, sovereign edge
- Ships with a BSI-aligned reference architecture for regulated German industries
- Has production deployments in EU regulated industries
- Is accepted as a Linux Foundation Europe project

### By 2027

- VS-NfD deployment profile (classified German government use cases)
- Official BSI guidance referencing Sentinel as a reference implementation
- Co-innovation contributions from European enterprises and research institutions
- A Sovereign Tech Fonds-funded core maintainer team

### By 2028

- The de facto open standard for AI decision trace infrastructure in Europe
- Commercial ecosystem of certified deployment partners and vertical applications built on the kernel
- Foundation governance fully independent of any single company

---

## What we are not building

We will not build a hosted SaaS product inside the open source project. We will not build a dashboard, a fine-tuning pipeline, or a model serving layer. We will not accept contributions that move Sentinel toward being a platform rather than a kernel.

Commercial products built on Sentinel — managed deployments, certified implementations, vertical applications — are welcome and expected. They do not live in this repository.

---

## Who should build this with us

**Enterprise AI teams** who are deploying agents in regulated environments and discovering that existing observability tools don't satisfy auditors, and existing governance platforms don't run on-prem.

**European defence and critical infrastructure organisations** who need to deploy AI in environments where US platforms are legally or politically excluded — and who have the most to gain from a sovereign reference implementation.

**Research institutions** who are building AI systems for public sector use and need an open, auditable middleware layer they can publish alongside their research.

**Cloud-native and DevOps engineers** who already run OPA, OpenTelemetry, and Kubernetes, and recognise that AI agent governance is the next layer of the same infrastructure problem.

**EU AI Act compliance engineers** who need a practical implementation of Article 12 logging that doesn't require buying a platform from a US vendor.

---

## How to be part of this

The fastest way to shape Sentinel's future is to deploy it. Use it on a real problem. File issues when it doesn't work. Open a PR when you fix something. Start an RFC when you have an architectural opinion.

The second fastest way is to bring a use case. If your organisation has a deployment context — regulated industry, classified environment, public sector — that tests Sentinel's architecture, open a GitHub Discussion.

---

## A note on commercial interests

The founder of Sentinel has a commercial interest in the sovereign AI space through a company building enterprise products on top of this kernel. This is not a conflict — it is the model. Red Hat built on Linux. HashiCorp built on Terraform. Elastic built on Elasticsearch. The open source project is not the commercial product, and the commercial product does not control the open source project.

The Apache 2.0 licence, the foundation governance model, and the public RFC process are the structural protections against any single commercial interest — including ours — capturing the project. They are non-negotiable and permanent.

---

*"The infrastructure projects that matter are the ones nobody owns."*
