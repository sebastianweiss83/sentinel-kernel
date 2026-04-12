# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 3.x     | ✓ Yes     |
| 2.x     | ✗ No      |
| 1.x     | ✗ No      |
| 0.x     | ✗ No      |

Only the current major version receives security patches.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email: **sebastian@swentures.com** (mark the subject `[sentinel-security]`).

Please include:

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact — in particular which of the three invariants
  is at risk
- Suggested fix, if known
- Your preferred language (English or German)

We will acknowledge within **48 hours** (7 days maximum during
holiday periods). Target resolution timelines:

- **Critical** — 30 days
- **High** — 60 days
- **Medium / Low** — 90 days

Reporters are credited in the CHANGELOG unless they ask otherwise.

## Security design principles

Sentinel is built around a small number of load-bearing invariants.
A vulnerability that breaks any of them is classified as critical.

1. **No network calls in the critical path.** Verified by CI
   (`tests/test_airgap.py`). A regression here means the air-gap
   promise is broken.
2. **Inputs are hashed by default.** `inputs_hash` uses SHA-256 on
   every trace. Raw inputs (`inputs_raw`) are opt-in per trace.
3. **Storage is append-only.** No `UPDATE`, no `DELETE`. Corrections
   are new linked traces, not mutations.
4. **Kill switch halts all processing immediately.** EU AI Act Art. 14.
   A vulnerability that bypasses `engage_kill_switch()` is critical.
5. **Optional dependencies are guarded with `ImportError`.** A
   missing optional package must never silently degrade the
   critical path.

## Scope

### In scope

- The `sentinel` Python package (kernel, storage, policy, scanner,
  compliance, dashboard).
- Optional integrations in `sentinel.integrations.*`.
- The reference Docker deployment in `demo/`.
- The sovereignty scanner's classification of installed packages.

### Out of scope

- The AI agents that Sentinel wraps — those are the caller's
  responsibility.
- The LLM providers the AI agents call.
- The underlying OS, container runtime, or hardware.
- Exploits requiring prior arbitrary code execution on the host.
- Issues that require physical access or social engineering.

## Known limitations

These are documented trade-offs, not vulnerabilities:

- **OTel export endpoint.** For full sovereignty, the collector
  should be self-hosted. A hostile collector can observe trace
  metadata (but not affect the critical path, because the local
  write always happens first).
- **PostgreSQL connection strings** may contain credentials. Use
  environment variables and a secrets manager. Sentinel does not
  log connection strings.
- **`LocalRegoEvaluator` requires the OPA binary.** Verify the OPA
  binary integrity out-of-band (e.g. against the project's GPG
  signature) before using it in a critical deployment.

## Cryptographic choices

- Input hashing: SHA-256 (hardcoded; no weak algorithms accepted).
- No encryption at rest in the kernel itself — inherit from OS/DB.
- No custom crypto. Sentinel does not implement cryptographic
  primitives.

## Audit status

No formal security audit has been performed yet. Community review
and responsible disclosure are the primary mechanisms for
identifying vulnerabilities at this stage. A BSI IT-Grundschutz
pre-engagement is planned for Q4 2026.

## CVE tracking

When a CVE is assigned, it will be referenced in the CHANGELOG
entry for the fix release and linked from this file.

Current CVEs: _none_.
