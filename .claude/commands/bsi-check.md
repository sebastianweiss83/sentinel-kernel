# /project:bsi-check
BSI IT-Grundschutz readiness check. Run before any formal BSI engagement.

## Usage: /project:bsi-check [file or "all"]

## APP.6 — Software
- [ ] No hardcoded credentials or secrets
- [ ] Input validation on all public interfaces
- [ ] Error messages do not leak internal state
- [ ] All dependencies pinned to exact versions
- [ ] No sensitive data in logs

## CON.1 — Cryptography
- [ ] Storage supports encryption at rest
- [ ] Strong encryption for all network transport
- [ ] No weak hash algorithms
- [ ] Key management documented in docs/bsi-profile.md

## CON.3 — Data protection
- [ ] No raw PII in traces by default
- [ ] Data minimisation applied
- [ ] Data residency asserted in every trace
- [ ] Deletion path exists and documented

## OPS.1.1.5 — Backup
- [ ] Traces exportable as NDJSON
- [ ] Backup and restore documented
- [ ] Air-gapped export works with no network

## VS-NfD prerequisites
- [ ] Air-gapped mode works end-to-end
- [ ] No mandatory internet connectivity in critical path
- [ ] Tested in network-isolated environment

## Output: Severity (BLOCKER/HIGH/MEDIUM/LOW) + BSI reference + fix + BSI submission blocker YES/NO
