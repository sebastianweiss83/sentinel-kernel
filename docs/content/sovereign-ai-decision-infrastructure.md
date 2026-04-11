# Why AI Decision Infrastructure Needs to Be Sovereign

_A technical note for CTOs deploying AI under the EU AI Act._
_Draft — 2026-04-11._

## 1. The decision record problem

Every AI agent running in production makes decisions. Most of them
are uncontroversial; some of them will eventually matter to a
regulator, an insurer, or a court. The distinction between the two
is knowable only in retrospect.

This is not a new problem. Database transactions get this right —
the log is authoritative, it is append-only, and it outlives the
process that wrote it. But AI agents have grown up inside
observability tools, which were built for debugging distributed
systems, not for evidence. An observability record is lossy by
design. It is sampled, compressed, rotated, and stored in whichever
backend you pay for this quarter. It is not evidence.

The EU AI Act (Regulation 2024/1689), Articles 12 and 13, closes
this gap for high-risk AI systems. By 2 August 2026, every such
system must produce automatic, tamper-resistant logging of every
decision it makes. The log must be durable, attributable, and
independently verifiable.

Most of the popular AI observability tooling today does not meet
this bar. It samples, it is cloud-hosted, and its retention is
controlled by contract rather than by law.

## 2. The jurisdiction problem

There is a second, less-discussed problem. The US CLOUD Act
(18 U.S.C. § 2713) requires US-incorporated companies to produce
data stored anywhere in the world, in response to a US legal
process, without notifying the owner of that data. Every major AI
platform vendor today is US-incorporated. Every EU-hosted datacenter
operated by one of them is still subject to the CLOUD Act through
the parent company.

The practical effect: if your AI decision records live in a US
vendor's pipeline — even in a Frankfurt region — your regulator
cannot independently assert that those records are under EU legal
control. Your regulator is right to be concerned.

"EU data centre" is not the same as "EU sovereign". Sovereignty is
a property of legal incorporation, not of physical location.

## 3. What Article 12 actually requires

Article 12 of the EU AI Act is short enough to read in one sitting.
The operative requirements are:

- **Automatic logging** — the system itself must produce records
  without relying on a human operator to switch them on.
- **Events throughout the lifecycle** — input classification,
  decision, output, any human override.
- **Enable identification** — the logs must let a reviewer identify
  the role of the log in the decision-making chain.
- **Retention proportionate to risk** — the operator defines the
  period, but it must be long enough to support the intended
  audit.

The enforcement deadline for Annex III (high-risk AI) is
**2 August 2026**. Penalties reach **€15M or 3% of global annual
turnover**, whichever is greater.

## 4. The architecture that satisfies it

An Article 12–compliant decision record layer has three
non-negotiable properties:

1. **Local-first.** The record must be written to storage the
   operator controls, in the critical path of every decision.
   Exports to observability tools can happen afterwards, but they
   must not be load-bearing.
2. **Append-only.** Corrections are new linked records, not
   mutations. This is the same property that makes database
   transaction logs defensible in court.
3. **Tamper-resistant.** Inputs are hashed at write time (SHA-256
   or stronger). Raw payloads are opt-in, never default, because
   regulators and data protection supervisors have opinions about
   what raw inputs are allowed to look like.

None of these are novel. They are database hygiene, applied to a
new kind of record.

## 5. Open source is necessary but not sufficient

Open source addresses one part of the problem — it makes the code
reviewable. It does not automatically address jurisdiction, air-
gap capability, or certification.

A sovereignty test for AI decision infrastructure has three parts:

- **Jurisdiction test.** Is there any US-incorporated entity in
  the runtime critical path? If yes, CLOUD Act exposure applies.
- **Air-gap test.** Does the critical path work with the network
  denied at the socket level? Not "mostly" — fully. If any
  optional exporter is required for the record to be durable, the
  test fails.
- **Certification test.** Can you point a regulator at a BSI IT-
  Grundschutz profile, a GDPR DPIA, or an equivalent document
  that maps the code to a recognised compliance framework?

Passing all three is the minimum for defence, healthcare,
financial services, and public administration deployments. Fewer
vendors pass all three than you might expect.

## 6. The manifesto-as-code concept

Sovereignty requirements today live in PowerPoint. Procurement
teams negotiate them, legal teams approve them, and engineering
teams are expected to honour them by hand. The gap between the
declared policy and the running system is where incidents happen.

A `SovereigntyManifest` closes that gap. It is the policy, and it
is simultaneously the check that runs in CI:

```python
from sentinel.manifesto import (
    SentinelManifesto,
    EUOnly,
    Required,
    GDPRCompliant,
    BSIProfile,
    AcknowledgedGap,
)

class OurPolicy(SentinelManifesto):
    jurisdiction = EUOnly()
    kill_switch  = Required()
    gdpr         = GDPRCompliant()
    bsi          = BSIProfile(
        status="pursuing",
        by="2026-Q4",
        evidence="docs/bsi-profile.md",
    )
    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No EU-sovereign CI with comparable UX yet",
    )
```

Run this against reality in CI. The output is a structured report
that distinguishes _violations_ from _acknowledged gaps with a
migration plan_. Procurement teams know the difference; the tool
should too.

The `AcknowledgedGap` type matters. Every non-sovereign project has
gaps today. Pretending otherwise damages trust. The honest position
is to name each gap, put a date on when it closes, and publish the
list.

## 7. Where we are today

`sentinel-kernel` is an Apache-2.0 Python implementation of this
architecture. Current capabilities:

- `@sentinel.trace` decorator for any agent, sync or async.
- SQLite, PostgreSQL, and filesystem storage backends; all
  append-only, all tested offline.
- Kill switch for EU AI Act Art. 14 human oversight.
- SimpleRule and LocalRego (OPA) policy evaluation.
- Runtime sovereignty scanner classifying 100+ packages.
- CI/CD scanner for GitHub Actions, CircleCI, GitLab CI, Jenkins,
  Drone, Dockerfiles, and Makefiles.
- EU AI Act automated checker for Articles 9, 12, 13, 14, 17.
- Manifesto-as-code with COMPLIANT / ACKNOWLEDGED / TARGETING
  statuses.
- LangChain, OpenTelemetry, LangFuse, and Haystack integrations.
- Self-contained HTML sovereignty reports.

344 tests passing, 96% coverage, 40/40 smoke test. No mandatory
network dependencies. Source at
`github.com/sebastianweiss83/sentinel-kernel`.

## 8. The road to BSI certification

The next milestones are:

- **v2.0 (Q4 2026)** — formal BSI IT-Grundschutz assessment
  alongside the EU AI Act enforcement date. The profile exists;
  see `docs/bsi-profile.md` in the repository for the current
  mapping across APP.6, CON.1, CON.2, OPS.1.1.3, SYS.1.6, and
  NET.1.2.
- **v2.1 (Q1 2027)** — VS-NfD deployment profile for classified
  German government deployments.
- **Linux Foundation Europe stewardship** — planned in parallel
  with the BSI engagement, as a neutral governance layer. See
  `docs/lf-europe-application/README.md`.

## 9. What you can do in the next hour

Three things, roughly in order of effort:

1. **Read Article 12** of the EU AI Act. It is 400 words. Every
   CTO shipping AI into regulated environments should know it
   cold.
2. **Audit your current decision record layer** against the three
   sovereignty tests. If it fails any of them, start writing the
   migration plan.
3. **Run `sentinel demo`** — install `sentinel-kernel`, run the
   command, read the sovereignty report. Decide whether the
   architecture matches your constraints.

The enforcement deadline is fixed. The architecture is not.

---

_This post is a draft. Feedback welcome via GitHub Discussions on
the_ [`sentinel-kernel`](https://github.com/sebastianweiss83/sentinel-kernel)
_repository or email._
