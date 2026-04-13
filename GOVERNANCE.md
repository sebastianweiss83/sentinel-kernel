# Governance

**Current state:** Single maintainer. RFC process for protocol changes. Pre-foundation.

---

## Roles

**Maintainer** — final authority on merges, RFC decisions, releases, and roadmap. Acts in the interest of the project. Commercial interests are disclosed in [VISION.md](VISION.md).

Maintainer: Sebastian Weiss ([@sebastianweiss83](https://github.com/sebastianweiss83))

**Contributors** — anyone who opens a PR, files an issue, or participates in an RFC. Contributions are evaluated on technical merit, sovereignty posture, and alignment with the [architecture principles](docs/architecture.md).

**Reviewers** *(planned)* — domain-scoped merge authority (e.g. storage backends, compliance mapping). Appointed by the maintainer when sustained contribution justifies it. Appointments recorded here.

**Advisory board** *(planned, see below)*.

---

## Decision-making

**Routine changes** — bug fixes, tests, docs, non-breaking additions — merged after code review. No formal process.

**Protocol changes require an RFC** — trace schema, `StorageBackend` interface, `PolicyEvaluator` contract, sovereignty assertions, governance changes. Process: author posts `docs/rfcs/RFC-[NNN]-[title].md`, opens a GitHub Discussion, 14-day comment period, maintainer decides, rationale recorded permanently.

**Releases** follow [Semantic Versioning](https://semver.org/). The public API is frozen as of v3.0 — see [docs/api-stability.md](docs/api-stability.md) for the STABLE / BETA / EXPERIMENTAL surface. Breaking changes to STABLE APIs require a major version bump and a minimum six-month deprecation notice.

---

## Advisory board (planned)

Four seats defined by domain expertise, not organisational affiliation. Advises on protocol direction, compliance requirements, and certification strategy. No merge authority.

| Seat | What they bring |
|---|---|
| Defence / aerospace product lead | Air-gapped deployment, mission-critical trace requirements, procurement compliance |
| Enterprise infrastructure CTO | Operational scale, integration with existing audit systems, availability constraints |
| Public sector architecture authority | BSI IT-Grundschutz, VS-NfD, EU AI Act enforcement, sovereignty verification |
| Systems integration lead | Multi-customer deployment patterns, partner ecosystem viability |

Seats belong to individuals, not organisations — a member who changes employer keeps their seat. Constituted when the project has active deployments in at least two of the four domains.

---

## Sovereignty as a governance concern

Sovereignty is not only a technical property. It is a governance constraint. No decision — dependency addition, integration acceptance, infrastructure choice — may introduce US CLOUD Act exposure in the critical path. This applies to the project's own infrastructure, not only to the code. Exceptions require an RFC.

---

## Evolution path

| Milestone | Governance change |
|---|---|
| **v0.2 — storage interface stable** | First reviewer appointments possible |
| **v0.3 — framework integrations** | Advisory board constituted (requires 2+ domain deployments) |
| **v1.0 — BSI reference implementation** | Foundation application submitted. Governance docs reviewed externally. |
| **Post-foundation acceptance** | Trademark transfer. Technical steering committee. Multi-maintainer structure. |

Target foundation: [Linux Foundation Europe](https://linuxfoundation.eu). If not accepted, an equivalent European open source foundation. The requirement is neutral stewardship — the specific institution is secondary.

---

## Licence and structural protections

Apache 2.0, permanently. No CLA. No relicensing mechanism. Governance concerns may be raised in a GitHub Discussion tagged `governance` — the maintainer must respond publicly within 14 days.

Changes to this document require an RFC.

---

*This document is versioned alongside the code. Its commit history is the governance record.*
