# sentinel-kernel

**Prove your AI decisions to the auditor. In Python. In five minutes.**

One decorator. One command. One PDF evidence pack. Runs fully offline.
No US cloud dependency. Apache 2.0, forever.

```bash
pipx install 'sentinel-kernel[pdf]'
sentinel quickstart
python hello_sentinel.py
sentinel evidence-pack          # produces audit.pdf
sentinel audit-gap              # shows what else your auditor will ask for
```

Sentinel is the enforcement and evidence layer for EU AI Act Art. 12
(logging), Art. 13 (transparency), Art. 14 (human oversight), and
Art. 17 (quality management traceability). It does **not** replace
Art. 9 risk management, Art. 10 data governance, Art. 11 technical
documentation, or Art. 15 accuracy and robustness controls — those
are organisational obligations above this layer. Run `sentinel
audit-gap` to see the exact split.

→ Full scope: [docs/eu-ai-act.md](docs/eu-ai-act.md) · Vision: [docs/vision.md](docs/vision.md) · Roadmap: [docs/roadmap.md](docs/roadmap.md)

<!-- SYNC_ALL_README_START -->
[![PyPI](https://img.shields.io/pypi/v/sentinel-kernel)](https://pypi.org/project/sentinel-kernel/)
[![Version](https://img.shields.io/badge/version-v3.1.0-blue)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)
[![Tests](https://img.shields.io/badge/tests-761%20passing-brightgreen)](https://github.com/sebastianweiss83/sentinel-kernel/actions)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/sebastianweiss83/sentinel-kernel/actions)
[![Status](https://img.shields.io/badge/status-production%2Fstable-brightgreen)](CHANGELOG.md)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Art.%2012%2F13%2F14%2F17-green)](docs/eu-ai-act.md)
<!-- SYNC_ALL_README_END -->

**Live preview:** https://sebastianweiss83.github.io/sentinel-kernel/
**Get started in 2 minutes:** [docs/getting-started.md](docs/getting-started.md)

## The 5-minute pilot

Four commands. Zero accounts. Zero API keys. Zero network.

```bash
pipx install 'sentinel-kernel[pdf]'   # or: pip install 'sentinel-kernel[pdf]'
sentinel quickstart                   # scaffolds hello_sentinel.py + ./.sentinel/
python hello_sentinel.py              # runs 10 decisions, writes traces to SQLite
sentinel evidence-pack                # writes audit.pdf from those traces
sentinel audit-gap                    # scores how audit-ready you actually are
```

The `[pdf]` extra pulls [reportlab](https://www.reportlab.com/) (BSD-3,
UK-based, pure Python) so `sentinel evidence-pack` can produce a
signed PDF your auditor can read. If you prefer to keep dependencies
to the absolute minimum, `pip install sentinel-kernel` still works —
every command except `evidence-pack` runs unchanged, and
`evidence-pack` itself tells you how to add the PDF extra.

`sentinel quickstart` generates a 12-line Python file wrapping a plain
function with `@sentinel.trace`. Running it produces ten immutable,
EU AI Act Art. 12-conformant decision records in
`./.sentinel/traces.db`. `sentinel evidence-pack` turns those records
into a signed PDF a compliance auditor can read. `sentinel audit-gap`
then tells you exactly what else is still missing — and whether you
can close it with the library, a deployment decision, or human
authorship.

### Why the plain-Python example is the golden path

The scaffolded example deliberately wraps a plain function, not an
LLM call. That means no OpenAI key, no LangChain, no Azure account,
no network. You see the value before you spend a single second on
credentials. When you are ready to wrap your real agent, the change
is one line. See [docs/integration-guide.md](docs/integration-guide.md)
for LangChain, CrewAI, AutoGen, and FastAPI integrations.

### What `sentinel audit-gap` shows you

```
Sentinel Audit Readiness — local pilot

  Scope            ./.sentinel/traces.db (10 traces)
  Profile          default

  +  Art. 12   Automatic logging                   10 traces recorded
  +  Art. 13   Transparency metadata               agent, model, policy fields populated
  +  Art. 17   Quality management record           append-only record present
  +  Data residency declared                       EU — EU_DE
  +  Offline / air-gapped storage                  local filesystem
  -  Art. 14   Human oversight (kill switch)       no kill switch registered
  -  Retention policy                              not configured
  -  Auditor-grade signing key                     ephemeral demo key in use
  -  Production storage backend                    using local SQLite
  -  Art. 11   Annex IV technical documentation    requires human authorship

  Audit readiness  [########......]   60 %

  Library gaps      (Sentinel can close these)         2
     > sentinel fix kill-switch
     > sentinel fix retention --days 2555

  Deployment gaps   (you must decide)                  2
     . Auditor-grade signing key
     . Production storage backend

  Organisational    (human authorship required)        1
     . Art. 11   Annex IV technical documentation

  The library gets you to ~70 %. The last 30 % depends on
  choices only your organisation can make: how long you
  retain, who signs, where traces live, and what your
  Annex IV document says.

  If you want to walk through this with someone who has
  done it for a regulated EU buyer:
      https://sentinel-kernel.eu/pilot
      30-minute call. No slides. No sales.

  Or close the gaps yourself — the library is sufficient.
```

`sentinel audit-gap` is re-runnable. Every `sentinel fix ...` you
apply moves the score. The split into library / deployment /
organisational tells you exactly which gaps you can close alone and
which ones need a human in a room.

### Install notes

```bash
# macOS (recommended — avoids PEP 668 "externally-managed-environment")
brew install pipx
pipx install sentinel-kernel

# Linux / Docker / CI
pip install sentinel-kernel

# Alternative (always works, even on systems where the bin dir is off-PATH)
python3 -m pip install sentinel-kernel
python3 -m sentinel quickstart
```

### Full-stack reference demo (Docker)

```bash
git clone https://github.com/sebastianweiss83/sentinel-kernel
cd sentinel-kernel/demo
docker compose up --build
```

Then open **http://localhost:3001** (Grafana, `admin` / `sentinel`).
The demo runs a realistic EU defence contractor scenario — policy
evaluation, kill switch, sovereignty scan — streaming live traces
to Grafana. See [demo/README.md](demo/README.md) for what to look at.

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

## How it works

Every time an autonomous system makes a decision, Sentinel answers
three questions:

1. **May it do this?** — A policy evaluator runs before execution. If
   the decision violates policy, Sentinel blocks it and records the
   triggering rule.

2. **Why did it want to?** — The decision is traced with input hash,
   policy result, model, agent, and sovereignty scope — tamper-resistant
   and append-only.

3. **Do we need to intervene?** — The Art. 14 kill switch halts every
   decision instantly. Overrides are recorded as linked trace entries;
   the original record is never mutated.

That is the trace + govern loop. Art. 12, Art. 13, and Art. 14 of the
EU AI Act are automated side-effects of this mechanism, not a separate
project. For the deeper CIO/auditor framing (four institutional
questions) see [docs/vision.md](docs/vision.md).

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

| | Sentinel | Cloud observability tools | Proprietary platforms |
|---|---|---|---|
| Sovereign decision records | ✓ | — | Vendor-jurisdicted |
| In-process policy evaluation | ✓ | — | — |
| Air-gapped operation | ✓ | — | — |
| BSI IT-Grundschutz path | ✓ | — | — |
| EU AI Act Art. 12/13/14/17 evidence layer | ✓ | — | Partial |
| Zero hard dependencies | ✓ | — | — |
| Apache 2.0 permanently | ✓ | Varies | — |
| US CLOUD Act exposure | **None** | Varies | **Unconditional** |

Sentinel is not an observability tool. It is not a content filter. It does not replace your LLM, your ML model, or your rule engine — it does not care which technology makes the decision. It wraps any Python function and produces a legally-valid, portable, sovereign record of every decision it makes.

---

## Who needs this

Sentinel is built for organisations deploying autonomous decisions in
regulated contexts. The urgent users, in order of regulatory pressure:

- **Financial services** — credit, fraud, AML and transaction approval
  under DORA-aligned logging and EU AI Act Annex III.
- **Insurance** — underwriting, claims triage and pricing with
  explainable decision records per GDPR Art. 22.
- **Public sector** — benefit eligibility, permit approval and
  administrative AI where transparency is statutory.
- **KRITIS / critical infrastructure** — operational AI decisions
  inside essential services under NIS2 and sector-specific regulation.
- **Defence** — logistics, procurement and dual-use assessment with
  air-gapped and classified deployment paths.

If your AI makes decisions that touch rights, access to services,
safety, or meaningful financial outcomes, EU AI Act Annex III likely
applies from 2 August 2026. Sentinel is the audit-trail layer for
those decisions. The architecture stays technology-agnostic — the
sectors above are where the deadline bites first.

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
# For PostgreSQL: from sentinel.storage.postgres import PostgresStorage
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
| **v3.1** | ✓ shipped | The Auditor Release — evidence pack, ci-check, runtime briefing |
| **v3.2** | Q3–Q4 2026 | LF Europe application + BSI IT-Grundschutz assessment |
| **v4.0** | 2026-27 | SovereignRouter |

## EU AI Act compliance

| Article | Requirement | Sentinel |
|---------|------------|---------|
| Art. 12 | Auto logging | ✓ Full — automated |
| Art. 13 | Transparency | ✓ Full — automated |
| Art. 14 | Human oversight | ✓ Full — kill switch |
| Art. 9  | Risk management | ~ Partial — policy traces |
| Art. 11 | Technical docs | → Human action — Annex IV required |
| Art. 17 | Quality mgmt | ✓ Full — continuous record |
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
  DECISION LAYER (your choice)
  LLMs · ML classifiers · Rule engines · Robotic systems
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

## Runtime Briefing

[Sentinel Runtime Briefing](https://sebastianweiss83.github.io/sentinel-kernel/runtime-briefing.html)
— operating picture, runtime walkthrough, decision record, evidence
route, deployment posture, and scope. Dark and light mode, keyboard
navigable, no framework, no tracking.

The Runtime Briefing is a **hand-authored architecture artefact**
served on GitHub Pages. It is not generated by the CLI and not part
of any local output. For artefacts you generate yourself locally —
sovereignty reports, compliance reports, signed PDF evidence packs,
attestations, NDJSON exports — see the next section.

## Viewing generated artefacts

Every `sentinel` subcommand that writes a file prints a
**copy-pasteable open command** on the line below `Wrote <path>` so
you can inspect the artefact immediately. The hint is
platform-aware — `open` on macOS, `xdg-open` on Linux, `start` on
Windows — and is identical across all file-writing commands.

```bash
$ sentinel report --output sovereignty_report.html
Wrote sovereignty_report.html
  → open 'sovereignty_report.html'

$ sentinel evidence-pack --output audit-q2.pdf --financial-sector
Wrote audit-q2.pdf
  → open 'audit-q2.pdf'

$ sentinel compliance check --html --output compliance.html
Wrote compliance.html
  → open 'compliance.html'

$ sentinel attestation generate --output attestation.json
Wrote attestation.json
  → open 'attestation.json'

$ sentinel export --output traces.ndjson --db traces.db
Exported 42 traces to traces.ndjson
  → open 'traces.ndjson'
```

**None of these commands auto-opens the file** — that would be
wrong for a sovereign CLI meant to run inside pipelines and
air-gapped environments. They print a hint the user (or a shell
alias) can act on.

The artefacts these commands produce are **local, operator-owned,
and never uploaded anywhere**. They are the opposite of the
hosted, cloud-visible „runs" of hyperscaler agent platforms.

| Artefact | Produced by | Format | Where it goes |
|---|---|---|---|
| Sovereignty / Compliance report | `sentinel report` | Self-contained HTML | Your filesystem |
| EU AI Act / DORA / NIS2 report | `sentinel compliance check --html / --json / --output` | HTML, JSON, or text | Your filesystem |
| Signed PDF evidence pack | `sentinel evidence-pack --output` | PDF (reportlab) | Your filesystem |
| Governance attestation | `sentinel attestation generate --output` | Self-contained JSON with SHA-256 digest | Your filesystem |
| Trace NDJSON export | `sentinel export --output` | NDJSON, one trace per line | Your filesystem |
| Runtime Briefing | Hand-authored, deployed on GitHub Pages | HTML (live web page) | `https://sebastianweiss83.github.io/sentinel-kernel/runtime-briefing.html` |

## Why it works for any autonomous system

The EU AI Act does not regulate language models. It regulates decisions.
Article 12 requires automatic, tamper-resistant logging of every decision
made by a high-risk system — regardless of the technology underneath.

An LLM, a gradient-boosted classifier, a rule engine, an industrial
robot: if it makes a high-risk decision, it needs a sovereign decision
record.

```python
# Works with any decision function
@sentinel.trace
async def my_decision(context: dict) -> dict:
    return await any_system.decide(context)
    # LLM, ML model, rule engine, robot control system
    # Sentinel doesn't care. It records the decision.
```

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

## Plug into CI/CD in 3 lines

```yaml
- run: pip install sentinel-kernel
- run: sentinel ci-check --manifesto manifesto.py:MyManifesto
```

`sentinel ci-check` runs the EU AI Act snapshot, the runtime
sovereignty scan, and (optionally) a manifesto check in-process,
with one aggregate exit code. Fully offline, air-gapped capable.
GitHub Actions, GitLab CI, Jenkins, and pre-commit snippets in
[docs/ci-cd-integration.md](docs/ci-cd-integration.md).

For auditors: `sentinel evidence-pack --output audit.pdf` generates
a signed, self-contained PDF evidence pack with EU AI Act / DORA /
NIS2 coverage, trace hash manifest, and sovereign attestation
appendix. Install via `pip install sentinel-kernel[pdf]`.

---

## Commercial support

The `sentinel-kernel` layer is Apache 2.0 forever. Commercial support
— deployment assistance, audit preparation, BSI pre-engagement,
custom policy libraries, incident response, SLA — is available for
regulated organisations that need an accountable party behind the
infrastructure. No hosted SaaS, no commercial fork, no CLOUD Act
exposure. Contact via GitHub Issues until a formal channel exists.
See [docs/commercial.md](docs/commercial.md).

---

## Documentation

**Core**
- [docs/vision.md](docs/vision.md) — the Sovereign Decision Kernel, in full
- [docs/roadmap.md](docs/roadmap.md) — three phases, Router design
- [docs/getting-started.md](docs/getting-started.md) — two-minute quickstart
- [docs/architecture.md](docs/architecture.md) — detailed architecture
- [docs/schema.md](docs/schema.md) — full trace schema reference
- [docs/api-stability.md](docs/api-stability.md) — API stability contract

**Compliance & certification**
- [docs/eu-ai-act.md](docs/eu-ai-act.md) — Article 12/13/14/17 mapping
- [docs/bsi-profile.md](docs/bsi-profile.md) — BSI IT-Grundschutz profile
- [docs/bsi-pre-engagement/README.md](docs/bsi-pre-engagement/README.md) — BSI pre-engagement package
- [docs/dora-compliance.md](docs/dora-compliance.md) — DORA financial regulation
- [docs/nis2-compliance.md](docs/nis2-compliance.md) — NIS2 critical infrastructure
- [docs/vsnfd-deployment.md](docs/vsnfd-deployment.md) — VS-NfD classified deployment

**Integrations & examples**
- [docs/integration-guide.md](docs/integration-guide.md) — framework integrations
- [docs/ci-cd-integration.md](docs/ci-cd-integration.md) — GitHub Actions, GitLab CI, Jenkins, pre-commit
- [docs/real-world-examples.md](docs/real-world-examples.md) — industry scenarios
- [examples/](examples/) — 13 runnable examples and 7 policy templates
- [demo/README.md](demo/README.md) — Docker Compose demo environment

**Ecosystem & governance**
- [docs/sovereignty.md](docs/sovereignty.md) — what sovereignty means
- [docs/landscape.md](docs/landscape.md) — how Sentinel relates to the ecosystem
- [docs/ecosystem.md](docs/ecosystem.md) — sovereign project registry
- [docs/rfcs/RFC-001-sovereignty-manifest.md](docs/rfcs/RFC-001-sovereignty-manifest.md) — SovereigntyManifest spec (draft)
- [rust-impl/](rust-impl/) — Rust reference implementation of RFC-001 (experimental)
- [GOVERNANCE.md](GOVERNANCE.md) — governance model
- [docs/commercial.md](docs/commercial.md) — commercial support scope
- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution guide
- [CHANGELOG.md](CHANGELOG.md) — version history

**Onboarding & operations**
- [docs/onboarding/technical-cofounder.md](docs/onboarding/technical-cofounder.md) — technical onboarding
- [docs/performance.md](docs/performance.md) — performance benchmarks
- [docs/releasing.md](docs/releasing.md) — release runbook
