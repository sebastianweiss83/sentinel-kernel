# For CISOs / security leads

You're evaluating whether Sentinel is safe to add to a regulated
stack. You need to answer: jurisdictional posture, dependency
footprint, attack surface, key management, air-gap behaviour,
incident-response story, and what you'd hand to your SecArch review.

## Jurisdictional posture (read first)

- **Jurisdiction:** Swentures UG (haftungsbeschränkt), Germany.
  Apache 2.0 forever — no CLA, no relicensing, no commercial fork.
- **CLOUD Act exposure in the critical path:** none. The critical path
  is a Python library + a local storage backend. No runtime call to a
  US-owned SaaS is possible on the default configuration.
- **Air-gapped:** supported and tested. `tests/test_airgap.py` runs
  the full trace+policy+report cycle with outbound network blocked.
- **Runtime dependencies:** zero required. `reportlab` (BSD-3, UK)
  under `[pdf]`. Everything else is optional per-integration.

## Dependency inventory — right now

```bash
sentinel scan --runtime --suggest-alternatives
sentinel scan --cicd --repo .
```

Output lists every installed package, parent-company jurisdiction, and
whether it makes a runtime network call. CI/CD scan inspects GitHub
Actions / GitLab CI / Jenkins config for US-owned control-plane
services. **Known acknowledged gap:** GitHub Actions itself is
US-controlled — declared in the repo policy (see
`sentinel/manifesto/base.py`) as a migration target to Forgejo.

## Signing / keys / attestation

Out of the box, `@sentinel.trace` emits *unsigned* traces. Production
deployments should use a persistent ML-DSA-65 keypair generated via
`sentinel keygen` and signed externally (HSM integration is operator
responsibility). See [security-posture.md](../security-posture.md)
for the HSM integration pattern and the explicit warning about
ephemeral keys being unverifiable across process restarts.

## Kill switch behaviour

EU AI Act Art. 14 requires human oversight. Sentinel's kill switch:

- `sentinel.engage_kill_switch(reason)` — halts every traced call in
  the process in ≤1 ms. Thread-safe.
- A DENY trace with `kill_switch=engaged` tag is written for every
  blocked call. The trace is immutable.
- `sentinel.disengage_kill_switch(reason)` — resumes. The disengagement
  is itself a linked trace entry.

The kill switch is a *runtime* control, not a deploy-time flag. It is
intended for the operator in the room, not the on-call engineer.

## What's NOT in the box (and should be)

- **RBAC over the trace store.** The store is a SQLite file. Anyone
  with filesystem read can read every trace. Remediation: PostgreSQL
  backend + database-native RBAC; or FilesystemStorage + FS-level
  ACLs. Multi-tenant segregation is per-`Sentinel()`-instance, not
  per-key. Documented roadmap; not shipped.
- **HSM abstraction.** No first-class AWS CloudHSM / Azure Key Vault /
  Thales PKCS#11 integration yet. Reference pattern in
  [security-posture.md](../security-posture.md).
- **SBOM export.** Planned, not shipped. For now:
  `pip list --format=json` + the `sentinel scan --json` output cover
  most of what a supply-chain audit needs.

## Incident-response story

A security incident touching Sentinel has three phases:

1. **Contain** — `sentinel.engage_kill_switch("security incident")`;
   halts decisions, continues to record evidence.
2. **Evidence** — `sentinel export --output incident-$(date -I).ndjson`;
   NDJSON per-trace record, portable, hash-verifiable.
3. **Verify** — `sentinel verify --all`; recomputes every stored
   hash against its stored data.

Full runbook: [incident-response.md](../incident-response.md) (if
present in your checkout; under construction).

## Reference documents

- [provability.md](../provability.md) — three provability conditions: jurisdictional integrity /
  air-gap / BSI-certifiable.
- [bsi-profile.md](../bsi-profile.md) — BSI IT-Grundschutz Baustein
  mapping.
- [vsnfd-deployment.md](../vsnfd-deployment.md) — classified-environment
  deployment profile.
- [provability.md#privacy-by-default-v320](../provability.md#privacy-by-default-v320)
  — why the default is hash-only.

## SecArch enquiry

Tracked publicly:
[Open a pilot enquiry on GitHub](https://github.com/sebastianweiss83/sentinel-kernel/issues/new?labels=pilot&template=pilot_enquiry.md).
For private follow-up, note that in the enquiry.
