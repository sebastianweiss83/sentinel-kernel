# BSI pre-engagement package

This directory is the conversation-starter for the formal BSI
IT-Grundschutz assessment of `sentinel-kernel`. It is generic —
no named customers, no classified information — and is meant to
be handed to BSI in the first meeting.

## The four modules

`sentinel-kernel` is **agility infrastructure for regulated AI**. It
sits in the execution path of any autonomous decision system and
implements four modules:

1. **Trace (v3.x, shipped).** Every autonomous decision becomes a
   structured, append-only decision record. EU AI Act Art. 12 is an
   automated side-effect of the interceptor. Optional ML-DSA-65
   (FIPS 204) signing for ten-plus-year retention, with keys on the
   operator's own infrastructure. See `docs/sentinel-evidence.md`.
2. **Policy (v3.x, shipped).** What the system may decide is
   policy-as-code, evaluated in-process, recorded in every trace.
   Art. 14 human oversight is implemented as a kill switch. Policy-
   as-Code runs as five named CI gates on every pull request. v3.1
   added `sentinel ci-check` (one-stop CI aggregator) and
   `sentinel evidence-pack` (signed PDF evidence pack for auditors).
3. **Evidence (v3.x, shipped).** Evidence packs, portable
   attestations, provability and compliance reports — the artefacts
   an auditor accepts. This is where regulated buyers spend the most
   time and where commercial engagement concentrates (HSM,
   RFC-3161 timestamping, long-term retention, BaFin-reporting
   templates).
4. **Federation (roadmap).** Multi-institution, concern-group, and
   supervisory-body aggregation. Architecturally anchored, not
   shipping. RFC-002 planned.

All four modules share a single `DecisionTrace` schema, a single
policy engine, and a single kill switch. There are no black boxes
in the critical path. See [docs/vision.md](../vision.md) for the
full product framing and [docs/roadmap.md](../roadmap.md) for phase
detail.

## Contents

- **`README.md`** — this file
- **`technical-summary.md`** — 2-page project summary
- **`architecture-overview.md`** — the 5-layer architecture
- **`test-evidence.md`** — how the test suite supports the BSI audit
- **`ai-act-mapping.md`** — EU AI Act Art. 12/13/14 mapping for BSI review

## Context

Sentinel is agility infrastructure for regulated AI, operated
under EU jurisdiction. Its three non-negotiable invariants are:

1. No US CLOUD Act exposure in the critical path.
2. Air-gapped operation must always work.
3. Apache 2.0, permanently — no CLA, no relicensing.

The software is at v3.3.0, production stable, with 773 tests
and 100% line and branch coverage enforced in CI. It is
designed for deployment in regulated environments including
VS-NfD-track defence and healthcare AI.

## What we need from BSI

- Confirmation that our IT-Grundschutz profile mapping is on
  track for the `APP.6`, `CON.1`, `CON.2`, `OPS.1.1.3`, `SYS.1.6`,
  and `NET.1.2` Bausteine (see `docs/bsi-profile.md`).
- Clarity on which Bausteine BSI expects to be covered by Sentinel
  itself vs. by the operator's deployment environment.
- A path forward for a VS-NfD profile (`docs/vsnfd-deployment.md`).

## What we provide

- Complete open source code under Apache 2.0.
- 773 automated tests with 100% line and branch coverage, enforced
  in CI, including 11 dedicated air-gap tests that deny the network
  at the socket level.
- Structured compliance reports for EU AI Act, DORA, NIS2.
- Signed PDF evidence packs via `sentinel evidence-pack` — cover
  page, framework coverage, hash manifest, portable attestation.
- Documented jurisdictional invariants with CI enforcement.
- Reproducible releases via PyPI trusted publisher (OIDC).

## Timeline

| Quarter | Milestone |
|---|---|
| 2026-Q2 | Informal BSI pre-engagement meeting |
| 2026-Q3 | Draft IT-Grundschutz profile reviewed |
| 2026-Q4 | Formal assessment begins |
| 2027-Q1 | Profile accepted; VS-NfD guidance iteration |

## Contact

**BSI Referat KI-Sicherheit**
Bundesamt für Sicherheit in der Informationstechnik
Godesberger Allee 185-189, 53175 Bonn

E-Mail: ki-sicherheit@bsi.bund.de
Web: https://www.bsi.bund.de/KI

**Recommended approach:**
1. Send `docs/bsi-pre-engagement/technical-summary.md` by email
2. Subject: "Sentinel — BSI IT-Grundschutz Pre-Engagement Anfrage"
3. Attach: `sentinel attestation generate --output attestation.json`
4. Expect response within 4-6 weeks

## Points of contact

- Maintainer: Sebastian Weiss (sebastian@swentures.com)
- Security disclosure: see `SECURITY.md` at the repo root.
