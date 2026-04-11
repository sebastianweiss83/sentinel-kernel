# Linux Foundation Europe — Application Preparation

This directory contains materials for the formal LF Europe
stewardship application, planned alongside v2.0.

## Why LF Europe

- Neutral governance for EU-sovereign AI infrastructure.
- Access to the LF Europe member network — vendors, integrators,
  regulators, other open-source projects with aligned goals.
- Signal to regulated-sector customers that the governance layer
  is not a single-vendor dependency.
- Required for some public-sector procurement frameworks.
- Alignment with the EU sovereignty agenda and the EU Open Source
  Policy.

## Prerequisites — checklist

- [x] Apache 2.0 license, permanent (see ADR-002)
- [x] Governance documentation complete
  ([GOVERNANCE.md](../../GOVERNANCE.md))
- [x] RFC process documented and exercised (RFC-001 accepted)
- [x] BSI IT-Grundschutz profile drafted and ready for
  pre-engagement ([docs/bsi-profile.md](../bsi-profile.md))
- [x] Stable public API with SemVer commitments
- [x] Test coverage ≥ 95% and air-gap CI gate
- [ ] Six months of API stability from v1.0 baseline
  (ticking — v1.0 = 2026-04-11)
- [ ] Two or more active contributors beyond the founder
- [ ] Production deployment evidence from at least one regulated-
  sector customer
- [ ] BSI pre-engagement meeting completed

## Current status

| Attribute | Value |
|---|---|
| API stable since | v1.0.0 (2026-04-11) |
| Governance docs | GOVERNANCE.md, CONTRIBUTING.md, SECURITY.md |
| RFC process | Documented, exercised (RFC-001 ACCEPTED) |
| BSI profile | Pre-engagement draft |
| Contributors | Seeking additional maintainers |
| Test coverage | 96% |
| License | Apache 2.0 |

## Application timeline

| Quarter | Milestone |
|---|---|
| 2026-Q2 | First informal contact with LF Europe |
| 2026-Q3 | Design partner pilot production deployment |
| 2026-Q4 | BSI pre-engagement completed; formal application submitted |
| 2027-Q1 | Advisory board constituted with named seats |
| 2027-Q2 | LF Europe stewardship decision |
| v2.0 | Full stewardship operational; trademark transfer |

## Materials index

This directory will expand as the application is drafted. Planned
contents (to be produced closer to the application date):

- `application-letter.md` — formal submission letter
- `technical-overview.md` — one-page project summary for LF Europe
  reviewers
- `community-profile.md` — contributor statistics, adoption
  evidence, deployment references
- `sustainability-plan.md` — how the project is funded and
  resourced post-stewardship
- `vs-other-foundations.md` — comparison with alternative
  stewardship options (Apache Foundation, Eclipse, OpenSSF)

## Decision criteria

We will proceed with LF Europe if:

1. LF Europe accepts the Apache-2.0-permanent commitment without
   a CLA requirement that enables relicensing.
2. At least two of the four advisory-board domains
   (defence, enterprise, public sector, systems integration) have
   a named representative willing to serve.
3. The BSI pre-engagement has produced a pathway that LF Europe
   stewardship does not obstruct.

If LF Europe stewardship is declined or proves incompatible, the
fallback is an equivalent European open-source foundation. The
requirement is neutral stewardship — the specific institution is
secondary. See GOVERNANCE.md for the formal commitment.
