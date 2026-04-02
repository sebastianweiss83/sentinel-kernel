# Governance

**Status:** Pre-foundation. Single-maintainer governance with documented processes. Designed to transition to foundation stewardship.

This document describes how decisions are made in the Sentinel project, who has authority over what, and how that authority is expected to evolve as the project matures.

---

## Current governance model

Sentinel is currently maintained by a single maintainer with full commit authority. All significant technical decisions are documented through the RFC process. The project operates transparently: decisions, rationale, and trade-offs are recorded in GitHub Discussions and commit history.

This is appropriate for an alpha-stage project. It is not the target state.

---

## Roles

### Maintainer

The maintainer has final authority over:
- Merge decisions on all pull requests
- RFC acceptance or rejection (after the comment period)
- Release tagging and publication
- Roadmap prioritisation
- Governance document changes

Current maintainer: Sebastian Weiss ([@sebastianweiss83](https://github.com/sebastianweiss83))

The maintainer is expected to act in the interest of the project, not a commercial entity. Where a conflict of interest exists, it must be disclosed. The maintainer's commercial activities are described in [VISION.md](VISION.md).

### Contributors

Anyone who submits a pull request, opens an issue, participates in an RFC discussion, or provides substantive feedback. Contributors have no formal authority but shape the project through participation. All contributions are evaluated on technical merit, sovereignty posture, and alignment with the [architecture principles](docs/architecture.md).

### Reviewers (planned)

As the contributor base grows, the project will appoint reviewers with domain-specific authority to approve pull requests in defined areas (e.g. storage backends, policy evaluation, documentation, compliance mapping). Reviewer appointments will be recorded in this document.

No reviewers are appointed at this time.

---

## Advisory Board (planned)

The project intends to establish an advisory board composed of domain experts who represent the deployment contexts Sentinel is designed for. The board advises on protocol direction, compliance requirements, and certification strategy. It does not have merge authority.

Advisory board seats are defined by domain expertise, not organisational affiliation. The intended composition:

| Seat | Domain | Perspective |
|---|---|---|
| Defence / aerospace product lead | Autonomous systems, classified environments, mission-critical AI | Air-gapped deployment, real-time trace requirements, procurement compliance |
| Enterprise transport / infrastructure CTO | Large-scale operations, fleet management, safety-critical systems | Operational scale, integration with existing audit infrastructure, availability requirements |
| Public sector architecture authority | Sovereign IT, government procurement, regulated deployment | BSI IT-Grundschutz, VS-NfD, EU AI Act enforcement, data sovereignty verification |
| Systems integration consulting lead | Commercial deployment, cross-industry implementation | Multi-customer deployment patterns, integration complexity, partner ecosystem viability |

Seats are filled by individuals, not organisations. An advisory board member who changes employer retains their seat — the expertise is theirs, not their employer's.

The advisory board will be constituted when the project has active deployments in at least two of the four domains above. Until then, design partner feedback serves this function informally.

---

## Decision-making process

### Day-to-day decisions

Bug fixes, documentation improvements, test additions, and non-breaking changes are merged by the maintainer (or, once appointed, by a reviewer with scope over the affected area). No formal process beyond code review.

### Significant technical decisions (RFC required)

Changes to the following require an RFC:

- Trace schema: mandatory fields, field semantics, field removal or rename
- `StorageBackend` interface
- `PolicyEvaluator` contract
- Sovereignty assertions or `DataResidency` enum
- Governance model changes

RFC process:

1. Author creates `docs/rfcs/RFC-[NNN]-[title].md`
2. Author opens a GitHub Discussion linking the RFC
3. A 14-day comment period follows — anyone may comment
4. The maintainer (or, once constituted, the advisory board for protocol-level changes) votes to accept or reject
5. The decision and rationale are recorded permanently in the Discussion

An RFC may be extended beyond 14 days if substantive objections remain unresolved.

### Release decisions

The maintainer decides when to cut a release. Release criteria for each milestone are documented in [docs/project-status.md](docs/project-status.md). Releases follow [Semantic Versioning](https://semver.org/). Breaking changes before 1.0 are expected and documented in [CHANGELOG.md](CHANGELOG.md).

---

## Contributor path

```
Contributor → Reviewer → Maintainer
```

**Contributor → Reviewer.** Demonstrated by sustained, high-quality contributions in a specific area (e.g. storage backends, compliance documentation, test infrastructure). The maintainer appoints reviewers and records the appointment in this document.

**Reviewer → Maintainer.** There is no automatic promotion. Additional maintainers will be appointed when the project requires it — specifically, when a single maintainer becomes a bottleneck for merge velocity or when foundation governance requires a multi-maintainer structure.

All role changes are recorded in this document with date and rationale.

---

## Foundation governance (planned)

Sentinel is designed for stewardship under [Linux Foundation Europe](https://linuxfoundation.eu). Formal engagement is planned alongside v1.0.

Foundation governance would mean:
- The Sentinel trademark is held by the foundation, not an individual or company
- Maintainer appointments are ratified by a technical steering committee
- The RFC process is governed by foundation bylaws
- No single commercial entity controls the roadmap

Until foundation governance is established, the current single-maintainer model applies. The transition plan:

1. **Pre-foundation (current):** Single maintainer. RFC process. Advisory board planned.
2. **Foundation application (v1.0):** Formal application to Linux Foundation Europe. Governance documents submitted for review.
3. **Foundation stewardship (post-acceptance):** Trademark transfer. Technical steering committee formed. Maintainer authority delegated per foundation bylaws.

If the Linux Foundation Europe application is not accepted, the project will pursue equivalent neutral governance through another European open source foundation. The requirement is neutral stewardship — the specific foundation is secondary.

---

## Licence

Apache 2.0, permanently. No Contributor Licence Agreement (CLA) is required. No contribution grants any party the right to relicence this software. This is a structural commitment, not a preference. See [LICENSE](LICENSE).

---

## Conflicts of interest

The maintainer has a commercial interest in the sovereign AI space. This is disclosed in [VISION.md](VISION.md). The structural protections are:

- Apache 2.0 licence with no relicensing mechanism
- No CLA that grants relicensing rights
- Public RFC process for all protocol-level decisions
- This governance document, versioned in the repository
- Planned foundation stewardship with independent oversight

If a contributor or advisory board member believes a decision is influenced by commercial interest rather than project interest, they may raise the concern in a GitHub Discussion tagged `governance`. The maintainer must respond publicly within 14 days.

---

## Amendments

Changes to this document require an RFC with a 14-day comment period. The RFC must explain what is changing and why. Amendments are recorded in the commit history of this file.

---

*This document is versioned alongside the code. Its history is the governance record.*
