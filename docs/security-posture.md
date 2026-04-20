# Security posture

*For CISOs, SecArch reviewers, and third-party security assessors.*

This document enumerates Sentinel's current security properties
honestly — including what is *not* yet in the product.

## Trust boundary

```
┌───────────────────────────────────────────────────────┐
│ Your process (Python runtime)                         │
│                                                       │
│ ┌─────────────────┐       ┌───────────────────────┐  │
│ │ Your agent /    │──1──▶│ @sentinel.trace        │  │
│ │ decision func.  │       │ (in-process, no RPC)  │  │
│ └─────────────────┘       └──┬────────────────────┘  │
│                              │                        │
│                              ▼ 2                      │
│                           Policy evaluator           │
│                           (in-process callable       │
│                            OR local OPA binary)      │
│                              │                        │
│                              ▼ 3                      │
│                        _finalise_trace               │
│                        (hash, redact, sign)          │
│                              │                        │
│                              ▼ 4                      │
│                           Storage                    │
│                  ┌────────────────────────────┐      │
│                  │ SQLite file / filesystem / │      │
│                  │ PostgreSQL connection      │      │
│                  └────────────────────────────┘      │
└───────────────────────────────────────────────────────┘
```

No outbound network call is made on the default code path. Steps
1–4 all execute inside the user's Python runtime.

## Runtime posture

- **Zero mandatory network calls.** Verifiable via `tests/test_airgap.py`,
  which runs the full cycle with outbound network blocked.
- **Zero mandatory runtime dependencies** beyond the Python stdlib.
  `reportlab` (BSD-3, UK) for PDF; optional per-integration deps for
  OTel, LangChain, etc.
- **Zero runtime shell execution** except the `LocalRegoEvaluator`,
  which spawns the local OPA binary when that evaluator is opted in.

## Data flow for a traced decision

1. Raw inputs enter `@sentinel.trace`'s internal frame.
2. Policy evaluator sees raw inputs (to decide ALLOW/DENY).
3. Signer sees the serialised trace including raw payloads.
4. `_finalise_trace` computes SHA-256 hashes and then — per the
   `store_inputs` / `store_outputs` flags — either keeps or discards
   the raw payloads before calling `storage.save`.

Raw payloads therefore **never reach disk** in the default
configuration, even though they are momentarily present in memory
during steps 1–3.

## Key management

- **Default (no signer).** Traces are unsigned by default. Per-trace
  SHA-256 content hashes combined with append-only storage provide
  tamper-evidence. This proves integrity against modification but does
  not authenticate the producer.
- **Persistent signer (recommended for non-repudiation).** Generate once
  with `sentinel keygen`, store the private key outside the repo (HSM,
  CI-secret store, filesystem with mode 600), pass the key path to the
  `Sentinel(signer=...)` constructor.

Algorithm default: `ML-DSA-65` (FIPS 204, BSI TR-02102-1 recommended,
post-quantum safe). Requires `sentinel-kernel[pqc]` extra
(liboqs backend).

### Custom signer pattern (e.g. HSM-backed)

Sentinel does not ship an HSM abstraction today. Operators who need
HSM-backed signing, or any algorithm other than ML-DSA-{44,65,87},
implement the minimal signer protocol themselves and pass the instance
to `Sentinel(signer=...)`. A sketch:

```python
from sentinel import Sentinel

class CustomSigner:
    """Illustrative adapter — operator-authored, not shipped by Sentinel.

    Implements the three-member signer protocol: ``sign``, ``verify``
    (omitted here for brevity), and an ``algorithm`` attribute.
    Replace the body of ``sign`` with your HSM vendor call, KMS call,
    or classical-algorithm backend of choice.
    """
    algorithm = "ML-DSA-65"

    def __init__(self, hsm_key_handle):
        self._handle = hsm_key_handle   # opaque to Sentinel

    def sign(self, payload: bytes) -> str:
        raw_sig = hsm_sign(self._handle, payload)   # vendor call
        return f"{self.algorithm}:{b64encode(raw_sig).decode()}"

sentinel = Sentinel(signer=CustomSigner(hsm_key_handle=...))
```

Tested integration examples for AWS CloudHSM, Azure Key Vault, and
Thales PKCS#11 are on the design-partner engagement path.

## Storage posture

- **SQLite (default).** Single-writer. File-system permissions are the
  only access control. Recommended for development and single-tenant
  production where you control the host.
- **FilesystemStorage.** NDJSON per day; naturally append-only. Ideal
  for air-gapped and WORM-mount setups.
- **PostgreSQL.** Multi-writer; use database-level roles and
  row-level-security for multi-tenant deployments.

## RBAC and multi-tenancy — honest status

Not shipped. Multi-tenant isolation today is per-`Sentinel()`
instance (different storage targets, different process boundaries).
Row-level segregation via the `project` field is available but is
*not* an access boundary — anyone with read on the file/DB sees
everything.

Target: PostgreSQL + Postgres RLS as the documented pattern. Target
timeline: v3.3.

## Known hardening items NOT in the box

| Item | Today | Target |
|---|---|---|
| SBOM export (`sentinel sbom`) | `pip list --format=json` + `sentinel scan --json` | v3.3 |
| HSM abstraction | Operator pattern above | v3.3 |
| Row-level RBAC | Absent | v3.3 |
| SLSA build provenance | Absent | v3.3 |
| OpenSSF Scorecard workflow | Absent | v3.3 |
| ISO 27001 / SOC 2 | Not pursued | Not on current roadmap |

## Incident-response runbook (minimal)

1. **Contain.** `sentinel.engage_kill_switch("incident-<id>")`. Every
   subsequent traced call is halted and recorded as a DENY with the
   engagement reason.
2. **Collect.** `sentinel export --output /secure/incident-<id>.ndjson`.
   Portable, hash-verifiable, no network.
3. **Verify.** `sentinel verify --all`. Any mismatch means the trace
   store was mutated after the fact.
4. **Rotate.** If a persistent signer was compromised, generate a
   new keypair, and note the transition point in your internal IR
   log — Sentinel does not implement key rotation inside a single
   trace stream.

Full runbook: `docs/incident-response.md` (under construction).

## Reporting a vulnerability

Open an issue with the `security` label, or email
`sentinel@swentures.com` for coordinated disclosure. No PGP key is
published yet; private follow-up via email is on request.
