# sentinel-kernel

**AI decisions. Recorded. Sovereign. Auditable.**

Every AI agent makes decisions. From **2 August 2026**, EU high-risk AI systems must prove it — automatically, tamper-resistantly, under EU law. Sentinel makes that possible in five minutes, with zero cloud dependencies, in any environment including air-gapped.

[![PyPI](https://img.shields.io/pypi/v/sentinel-kernel)](https://pypi.org/project/sentinel-kernel/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)
[![Tests](https://img.shields.io/badge/tests-71%20passing-brightgreen)](https://github.com/sebastianweiss83/sentinel-kernel/actions)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%2012%2F13%2F17-green)](docs/eu-ai-act.md)

---

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

| Version | Target | Milestone |
|---|---|---|
| **v0.1** | Now | Kernel, in-process policy eval, SQLite + Filesystem storage, 71 tests |
| **v0.2** | Q2 2026 | PostgreSQL, stable storage interface |
| **v0.3** | Q3 2026 | LangChain integration, OpenTelemetry export, kill switch (Art. 14) |
| **v0.4** | Q3 2026 | Air-gapped validation suite, classified deployment guide |
| **v1.0** | Q4 2026 | BSI IT-Grundschutz assessment — certified sovereign |
| **v1.1** | Q1 2027 | VS-NfD classified deployment profile |

---

## EU AI Act compliance

| Article | Requirement | Sentinel |
|---|---|---|
| Art. 9 | Risk management | Policy eval recorded in every trace |
| Art. 12 | Automatic tamper-resistant logging | Every decision produces a trace automatically |
| Art. 13 | Transparency to deployers | Policy name, version, result in every trace |
| Art. 14 | Human oversight + kill switch | Override mechanism → linked immutable trace |
| Art. 17 | Quality management | Continuous tamper-resistant record |

Enforcement for Annex III high-risk AI: **2 August 2026**. Penalties up to €15M or 3% of global annual turnover.

Full mapping: [docs/eu-ai-act.md](docs/eu-ai-act.md)

---

## Architecture

```
Your AI agents (any framework, any model)
         │
         ▼
  ┌─────────────────────┐
  │   Sentinel Kernel   │  ← wraps any agent call
  │                     │
  │  Interceptor        │  ← captures inputs, timing, context
  │  Policy Evaluator   │  ← in-process: Rego / Python / custom
  │  Trace Serializer   │  ← SHA-256 hashed, schema-versioned
  └──────────┬──────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
 SQLite  PostgreSQL  Filesystem
                     (NDJSON, air-gapped)
```

**Critical path guarantees:**
- Zero hard dependencies
- Zero network calls at runtime
- Zero US CLOUD Act exposure
- Full offline / air-gapped operation

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

## License

Apache 2.0. [Full text.](https://www.apache.org/licenses/LICENSE-2.0)

No BSL. No commercial-only features. No relicensing. Ever.

---

## Governance

Sentinel is pursuing stewardship under **Linux Foundation Europe**. Until confirmed, the project is maintained independently with all significant decisions made through the RFC process in GitHub Discussions.

---

## Documentation

- [docs/schema.md](docs/schema.md) — full trace schema reference
- [docs/eu-ai-act.md](docs/eu-ai-act.md) — Article 12/13/14/17 mapping
- [docs/integration-guide.md](docs/integration-guide.md) — framework integrations
- [docs/sovereignty.md](docs/sovereignty.md) — what sovereignty means
- [docs/bsi-profile.md](docs/bsi-profile.md) — BSI IT-Grundschutz profile
- [docs/landscape.md](docs/landscape.md) — how Sentinel relates to LLMOps ecosystem
- [docs/architecture.md](docs/architecture.md) — detailed architecture
- [docs/quickstart.md](docs/quickstart.md) — extended quickstart guide
- [VISION.md](VISION.md) — strategic vision
- [ROADMAP.md](ROADMAP.md) — detailed milestones
- [GOVERNANCE.md](GOVERNANCE.md) — governance model
- [CHANGELOG.md](CHANGELOG.md) — version history
