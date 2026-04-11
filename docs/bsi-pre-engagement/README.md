# BSI pre-engagement package

This directory is the conversation-starter for the formal BSI
IT-Grundschutz assessment of `sentinel-kernel`. It is generic —
no named customers, no classified information — and is meant to
be handed to BSI in the first meeting.

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

The software is at v2.0, production stable, with 503+ tests and
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
- 503+ automated tests with 100% line coverage, including 11
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

## Points of contact

- Maintainer: Sebastian Weiss (sebastian@swentures.com)
- Security disclosure: see `SECURITY.md` at the repo root.
