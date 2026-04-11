# sentinel-kernel

**The Sovereign AI Kernel.**

Three layers between your business logic and your AI models:

- **Trace** — every decision recorded, sovereign, tamper-resistant
- **Govern** — what AI may decide, policy-as-code, kill switch
- **Route** *(v4.0)* — which model decides what, based on sovereignty policy

No vendor lock-in. No US CLOUD Act. No deployment strategists.
Apache 2.0, permanently.

EU AI Act Annex III enforcement: **2 August 2026**. Sentinel turns that
legal requirement into a technical fact — in five minutes, with zero
cloud dependencies, in any environment including air-gapped.

→ Full vision: [docs/vision.md](docs/vision.md) · Full roadmap: [docs/roadmap.md](docs/roadmap.md)

<!-- SYNC_ALL_README_START -->
[![PyPI](https://img.shields.io/pypi/v/sentinel-kernel)](https://pypi.org/project/sentinel-kernel/)
[![Version](https://img.shields.io/badge/version-v3.0.3-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)
[![Tests](https://img.shields.io/badge/tests-608%20passing-brightgreen)](https://github.com/sebastianweiss83/sentinel-kernel/actions)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/sebastianweiss83/sentinel-kernel/actions)
[![Status](https://img.shields.io/badge/status-production%2Fstable-brightgreen)](CHANGELOG.md)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%2012%2F13%2F14%2F17-green)](docs/eu-ai-act.md)
<!-- SYNC_ALL_README_END -->

**Live preview:** https://sebastianweiss83.github.io/sentinel-kernel/
**Get started in 2 minutes:** [docs/getting-started.md](docs/getting-started.md)

## Quick demo

```bash
pip install sentinel-kernel
sentinel demo  # 50 decisions, kill switch, compliance check, report
```

---

## Quick demo — full stack in one command

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel
cd sentinel-kernel/demo
docker compose up --build
```

Then open **http://localhost:3001** (Grafana, `admin` / `sentinel`).

The demo runs a realistic EU defence contractor scenario — policy
evaluation, kill switch (Art. 14), document analysis, sovereignty
scan — and streams live traces to Grafana. See
[demo/README.md](demo/README.md) for what to look at.

## Install

```bash
pip install sentinel-kernel
```

## Five minutes to your first sovereign trace

```python
from sentinel import Sentinel

sentinel = Sentinel()  # local storage, zero config, no network

@sentinel.trace
async def approve_request(payload: dict) -> dict:
    # your existing agent logic — unchanged
    return await your_agent.run(payload)

result = await approve_request({"action": "approve", "amount": 50000})
```

That's it. Every call now produces a tamper-resistant decision record:

```json
{
  "trace_id": "01hx7k9m2n3p4q5r6s7t8u9v0w",
  "timestamp": "2026-04-01T14:23:41.234Z",
  "agent": "approve_request",
  "model": "mistral/large-2",
  "policy_result": "ALLOW",
  "inputs_hash": "sha256:a3f8c2d19e4b67f0c1a5d8e2b9c3f4a7",
  "output": {"decision": "approved"},
  "sovereign_scope": "EU",
  "data_residency": "local",
  "schema_version": "1.0.0"
}
```

Stored locally. No cloud account. No API key. No network call.

---

## With policy evaluation

```python
from sentinel import Sentinel, DataResidency
from sentinel.policy import SimpleRuleEvaluator
from sentinel.storage import FilesystemStorage

def within_threshold(ctx: dict) -> tuple[bool, str | None]:
    if ctx.get("amount", 0) > ctx.get("agent_threshold", 0):
        return False, "amount_exceeds_threshold"
    return True, None

# works fully offline — classified environments, air-gapped networks
sentinel = Sentinel(
    storage=FilesystemStorage("/mnt/traces"),
    policy_evaluator=SimpleRuleEvaluator({
        "policies/procurement.py": within_threshold,
    }),
    sovereign_scope="EU",
    data_residency=DataResidency.EU_DE,
)

@sentinel.trace(policy="policies/procurement.py")
async def evaluate_procurement(ctx: dict) -> dict:
    return await agent.run(ctx)
```

For OPA/Rego policies:

```python
from sentinel import Sentinel
from sentinel.policy import LocalRegoEvaluator

sentinel = Sentinel(
    policy_evaluator=LocalRegoEvaluator(opa_binary="opa"),
    # OPA runs in-process — no network, no OPA server
)

@sentinel.trace(policy="policies/procurement.rego")
async def evaluate_procurement(ctx: dict) -> dict:
    return await agent.run(ctx)
```

---

## What Sentinel does. What it doesn't.

| | Sentinel | LLM observability tools | Proprietary AI platforms |
|---|---|---|---|
| Sovereign decision records | ✓ | — | Vendor-jurisdicted |
| In-process policy evaluation | ✓ | — | — |
| Air-gapped operation | ✓ | — | — |
| BSI IT-Grundschutz path | ✓ | — | — |
| EU AI Act Art. 12 compliance | ✓ | — | Partial |
| Zero hard dependencies | ✓ | — | — |
| Apache 2.0 permanently | ✓ | Varies | — |
| US CLOUD Act exposure | **None** | Varies | **Unconditional** |

Sentinel is not an observability tool. It is not a content filter. It does not replace your LLM or your agent framework. It wraps them — and produces a legally-valid, portable, sovereign record of every decision they make.

---

## Deployment

**Local / development**
```python
sentinel = Sentinel()  # SQLite, no config
```

**On-premise enterprise**
```python
from sentinel import Sentinel, DataResidency
from sentinel.storage import SQLiteStorage

sentinel = Sentinel(
    storage=SQLiteStorage("/var/lib/sentinel/traces.db"),
    sovereign_scope="EU",
    data_residency=DataResidency.EU_DE,
)
# PostgreSQL storage planned for v0.2
```

**Air-gapped / classified**
```python
from sentinel import Sentinel, DataResidency
from sentinel.storage import FilesystemStorage

sentinel = Sentinel(
    storage=FilesystemStorage("/mnt/traces"),
    data_residency=DataResidency.AIR_GAPPED,
)
# zero network connectivity required
# traces written as NDJSON, one file per day
```

---

## Why sovereignty matters

The US CLOUD Act (18 U.S.C. § 2713) requires US-incorporated companies to produce data stored anywhere in the world on valid legal process. This applies to EU data centres operated by US companies. No contract eliminates it.

EU AI Act Article 12 mandates automatic, tamper-resistant logging for high-risk AI systems from **2 August 2026**. Decision logs that are simultaneously accessible to US authorities do not satisfy this requirement from EU jurisdiction.

Sentinel's critical path — interceptor, policy evaluation, trace emission, storage — contains no US-owned components. This is architectural. Not a configuration option.

---

## Roadmap

| Phase | Status | What |
|---|---|---|
| **Trace + Govern** | ✓ v3.0 | Sovereign traces, policy-as-code, kill switch |
| **Certify** | → 2026 | BSI IT-Grundschutz, LF Europe |
| **Route** | → v4.0 | Sovereign model router |
| **Ecosystem** | 2027+ | EU build pipeline, multi-language |

Full phase detail, including the SovereignRouter design and the
market thesis, lives in [docs/roadmap.md](docs/roadmap.md).

### Version history

| Version | Status | Milestone |
|---------|--------|-----------|
| **v1.0** | ✓ shipped | Core production baseline |
| **v1.5** | ✓ shipped | DORA, NIS2, VS-NfD compliance |
| **v2.0** | ✓ shipped | Production stable, BSI ready |
| **v2.1** | ✓ shipped | BudgetTracker, attestations, CrewAI, AutoGen |
| **v2.2** | ✓ shipped | ML-DSA-65 quantum-safe signing |
| **v2.3** | ✓ shipped | LangFuse sovereignty panel |
| **v2.4** | ✓ shipped | Rust RFC-001 implementation |
| **v3.0** | ✓ shipped | API frozen, BSI pre-engagement package |
| **v3.1** | Q3 2026 | LF Europe application |
| **v3.2** | Q4 2026 | BSI IT-Grundschutz assessment |
| **v4.0** | 2026-27 | SovereignRouter |

## EU AI Act compliance

| Article | Requirement | Sentinel |
|---------|------------|---------|
| Art. 12 | Auto logging | ✓ Full — automated |
| Art. 13 | Transparency | ✓ Full — automated |
| Art. 14 | Human oversight | ✓ Full — kill switch |
| Art. 9  | Risk management | ~ Partial — policy traces |
| Art. 11 | Technical docs | ~ Partial — traces as evidence |
| Art. 17 | Quality mgmt | ~ Partial — continuous record |
| Art. 16 | Provider obligations | ~ Partial — logging covered |
| Art. 26 | Deployer obligations | ~ Partial — logging + oversight |
| Art. 10 | Data governance | → Human action |
| Art. 15 | Accuracy | → Human action |
| Art. 72 | GPAI (if applicable) | ~ Conditional |

**Sentinel never overclaims.** Articles requiring human action are
clearly marked. Partial articles are those where Sentinel produces
the evidence but an organisational deliverable must still be written.

Enforcement for Annex III high-risk AI: **2 August 2026**. Penalties up to €15M or 3% of global annual turnover.

Full mapping: [docs/eu-ai-act.md](docs/eu-ai-act.md)

---

## Architecture

```
Your business logic
        │
        ▼
┌─────────────────────────────────────────┐
│           SENTINEL KERNEL               │
│                                         │
│  ┌───────────────┐  ┌─────────────────┐ │
│  │    GOVERN ✓   │  │   ROUTE → v4.0  │ │
│  │  Policy-code  │  │  Which model?   │ │
│  │  Kill switch  │  │  Sovereignty?   │ │
│  │  Preflight    │  │  Data class?    │ │
│  └───────────────┘  └─────────────────┘ │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │          TRACE ✓                │    │
│  │  Sovereign · Tamper-resistant   │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
        │
        ▼
  MODEL LAYER (your choice)
  Claude · Mistral · Llama · Kimi · local
  Switch anytime. No lock-in.
        │
        ▼
  SOVEREIGN STORAGE
  SQLite · PostgreSQL · NDJSON
  Your infrastructure. Always.
```

**Critical-path guarantees:**
- Zero hard dependencies
- Zero network calls at runtime
- Zero US CLOUD Act exposure
- Full offline / air-gapped operation

## Why not Palantir AIP

Palantir AIP costs €5–20M per year. It is US-incorporated (CLOUD Act
applies to all your data). It requires deployment strategists. It is
proprietary.

When LLMs guide their own integration — and that is already happening —
the deployment-strategist model collapses. What survives is the trusted
kernel underneath: policy, audit trail, model router, sovereignty proof.

Sentinel is that kernel. Open source. EU sovereign. Self-service.
Apache 2.0, permanently. The full argument is in [docs/vision.md](docs/vision.md).

---

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.

Every integration must document its sovereignty posture. Schema changes require an RFC. Breaking changes to the trace format go through a 14-day comment period.

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel
cd sentinel-kernel
pip install -e ".[dev]"
pytest
```

---

---

If Sentinel helps you meet EU AI Act requirements, consider giving
it a ⭐ on GitHub — it helps others find the project.

---

## License

Apache 2.0. [Full text.](https://www.apache.org/licenses/LICENSE-2.0)

No BSL. No commercial-only features. No relicensing. Ever.

---

## Governance

Sentinel is pursuing stewardship under **Linux Foundation Europe**. Until confirmed, the project is maintained independently with all significant decisions made through the RFC process in GitHub Discussions.

---

## Documentation

- [docs/vision.md](docs/vision.md) — the Sovereign AI Kernel, in full
- [docs/roadmap.md](docs/roadmap.md) — three phases, Router design
- [docs/getting-started.md](docs/getting-started.md) — two-minute quickstart
- [docs/real-world-examples.md](docs/real-world-examples.md) — industry scenarios
- [docs/schema.md](docs/schema.md) — full trace schema reference
- [docs/eu-ai-act.md](docs/eu-ai-act.md) — Article 12/13/14/17 mapping
- [docs/integration-guide.md](docs/integration-guide.md) — framework integrations
- [docs/sovereignty.md](docs/sovereignty.md) — what sovereignty means
- [docs/ecosystem.md](docs/ecosystem.md) — sovereign AI project registry
- [docs/rfcs/RFC-001-sovereignty-manifest.md](docs/rfcs/RFC-001-sovereignty-manifest.md) — SovereigntyManifest spec (draft)
- [docs/bsi-profile.md](docs/bsi-profile.md) — BSI IT-Grundschutz profile
- [demo/README.md](demo/README.md) — Docker Compose demo environment
- [examples/](examples/) — 13 runnable examples and 5 policy templates
- [docs/landscape.md](docs/landscape.md) — how Sentinel relates to LLMOps ecosystem
- [docs/architecture.md](docs/architecture.md) — detailed architecture
- [docs/releasing.md](docs/releasing.md) — release runbook
- [CLAUDE_MEGA_PROMPT.md](CLAUDE_MEGA_PROMPT.md) — persistent Claude Code reference
- [VISION.md](VISION.md) — strategic vision
- [ROADMAP.md](ROADMAP.md) — detailed milestones
- [GOVERNANCE.md](GOVERNANCE.md) — governance model
- [CHANGELOG.md](CHANGELOG.md) — version history
