# BSI pre-engagement package

This directory is the conversation-starter for the formal BSI
IT-Grundschutz assessment of `sentinel-kernel`. It is generic —
no named customers, no classified information — and is meant to
be handed to BSI in the first meeting.

## The three-layer kernel

`sentinel-kernel` is the **Sovereign AI Kernel**. It sits between
business logic and AI models and implements three layers:

1. **Trace (v3.0 shipped).** Every AI decision becomes a structured,
   append-only sovereign record. EU AI Act Art. 12 is an automated
   side-effect of the interceptor. Optional ML-DSA-65 (FIPS 204)
   signing, with keys on the operator's own infrastructure.
2. **Govern (v3.0 shipped).** What the AI may decide is policy-as-code,
   evaluated in-process, recorded in every trace. Art. 14 human
   oversight is implemented as a kill switch. Manifesto-as-code runs
   as five named CI theses on every pull request.
3. **Route (v4.0 roadmap).** The SovereignRouter — the same policy
   engine that governs what may be decided selects which model
   handles each decision, based on data classification and
   sovereignty requirements. RFC-002 is in discussion.

All three layers share a single DecisionTrace schema, a single policy
engine, and a single kill switch. There are no black boxes in the
critical path. See [docs/vision.md](../vision.md) for the full
architecture and [docs/roadmap.md](../roadmap.md) for phase detail.

## Contents

- **`README.md`** — this file
- **`technical-summary.md`** — 2-page project summary
- **`architecture-overview.md`** — the 5-layer architecture
- **`test-evidence.md`** — how the test suite supports the BSI audit
- **`ai-act-mapping.md`** — EU AI Act Art. 12/13/14 mapping for BSI review

## Context

Sentinel is an EU-sovereign AI decision middleware kernel. Its
three non-negotiable invariants are:

1. No US CLOUD Act exposure in the critical path.
2. Air-gapped operation must always work.
3. Apache 2.0, permanently — no CLA, no relicensing.

The software is at v3.0, production stable, with 615+ tests and
100% line coverage. It is designed for deployment in regulated
environments including VS-NfD-track defence and healthcare AI.

## What we need from BSI

- Confirmation that our IT-Grundschutz profile mapping is on
  track for the `APP.6`, `CON.1`, `CON.2`, `OPS.1.1.3`, `SYS.1.6`,
  and `NET.1.2` Bausteine (see `docs/bsi-profile.md`).
- Clarity on which Bausteine BSI expects to be covered by Sentinel
  itself vs. by the operator's deployment environment.
- A path forward for a VS-NfD profile (`docs/vsnfd-deployment.md`).

## What we provide

- Complete open source code under Apache 2.0.
- 615+ automated tests with 100% line coverage, including 11
  dedicated air-gap tests that deny the network at the socket level.
- Structured compliance reports for EU AI Act, DORA, NIS2.
- Documented sovereignty invariants with CI enforcement.
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
