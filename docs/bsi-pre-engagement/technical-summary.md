# Sentinel — Technical Summary (BSI pre-engagement)

## What it is

`sentinel-kernel` is an open-source Python library that implements
agility infrastructure for regulated AI: it sits in the execution
path of any autonomous decision system and produces an auditor-
grade evidence record for every decision it makes. It is the
technical layer regulated European enterprises need to satisfy
EU AI Act Art. 12 (automatic logging), Art. 13 (transparency),
and Art. 14 (human oversight) under EU jurisdiction. It is
designed to run in air-gapped classified environments.

## Target deployments

- Defence and aerospace procurement AI (VS-NfD track)
- Healthcare clinical decision support
- Financial sector (DORA compliance)
- Critical infrastructure operators (NIS2 compliance)
- Public-sector AI transparency

## Architecture in one paragraph

Five layers. An interceptor wraps any Python callable with
`@sentinel.trace`. The wrapped call flows through a pluggable
policy evaluator (SimpleRule, LocalRego/OPA, or custom) that emits
an `ALLOW`, `DENY`, or `EXCEPTION_REQUIRED` verdict. The verdict
and the hashed inputs/outputs are written synchronously to a
pluggable storage backend (SQLite, Filesystem, PostgreSQL) — the
local write is always in the critical path. Optional exporters
(OTel, LangFuse, Prometheus textfile) run *after* the local write
and cannot gate it. A kill switch halts all further agent calls
instantly for Art. 14 human oversight.

## Sovereignty posture

- **Zero US CLOUD Act exposure** in the runtime critical path —
  verified by `scripts/check_sovereignty.py` in CI.
- **Air-gap capable** — `tests/test_airgap.py` runs the entire
  critical path with the network denied at the socket level.
- **Apache 2.0 permanently** — no CLA, no relicensing mechanism.
- **Open source knowledge base** — `sentinel/scanner/knowledge.py`
  classifies 100+ Python packages by parent company and
  jurisdiction. EU-sovereign alternatives are listed.

## Automated compliance

Three checkers ship in the library:

- **EU AI Act** — Art. 9, 12, 13, 14, 17 automated
- **DORA** — Art. 6, 17 automated (Art. 24, 28 operator action)
- **NIS2** — Art. 21, 23 automated (Art. 20, 24 operator action)

Each checker is honest about the split: articles that inherently
require human action are marked `ACTION_REQUIRED` with a short
explanation. No pretending that software can automate governance.

## Test evidence

- **686 tests** across unit, integration, and air-gap suites.
- **100% line and branch coverage** — enforced in CI via
  `--cov-fail-under=100`. No module is under the bar.
- **40/40 smoke test** — a 40-step end-to-end validation that
  runs on every release.
- **11 dedicated air-gap tests** that deny `socket.socket()` at
  the patch level and run the full `@sentinel.trace` path.
- **Trace integrity verification** — `Sentinel.verify_integrity()`
  re-hashes stored inputs/outputs and compares against stored
  hashes. This is the feature that makes Sentinel defensible in
  court: every trace can be independently verified as unmodified.
- **Signed PDF evidence pack** — `sentinel evidence-pack` bundles
  traces in a window with framework coverage, hash manifest, and
  a sovereign attestation. Reproducible, offline-verifiable,
  suitable as an audit binder artefact.

## What Sentinel does NOT cover

- Physical security of the deployment environment
- Network segmentation and firewall rules
- Personnel security clearances
- HSM / PKI / certificate management
- The AI models themselves — those are separately governed

These are operator responsibilities documented in
`docs/vsnfd-deployment.md`.

## Governance

- **Maintainer:** Sebastian Weiss (sebastian@swentures.com)
- **License:** Apache 2.0, permanently
- **Governance doc:** `GOVERNANCE.md` at the repo root
- **RFC process:** documented in `CONTRIBUTING.md`
- **Target foundation:** Linux Foundation Europe stewardship,
  planned for v3.2 alongside the BSI IT-Grundschutz assessment

## References

- Repo: https://github.com/sebastianweiss83/sentinel-kernel
- PyPI: https://pypi.org/project/sentinel-kernel/
- EU AI Act: Regulation (EU) 2024/1689
- DORA: Regulation (EU) 2022/2554
- NIS2: Directive (EU) 2022/2555
- BSI IT-Grundschutz: see `docs/bsi-profile.md`
