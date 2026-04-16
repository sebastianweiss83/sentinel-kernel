# Provability — what it means, and what it requires

Provability is what regulated buyers actually need. Sovereignty
is a consequence of provability, not a headline.

Open source is not the same as provable. A library can be
Apache 2.0 and still route your data through US infrastructure.
A self-hosted tool can run on EU servers operated by a US
company — still subject to the US CLOUD Act. Provability is a
property of the runtime, not just the code.

## The three provability conditions

**1. Jurisdictional integrity — is there a US-owned component in the critical path?**

The US CLOUD Act (18 U.S.C. § 2713) requires US-incorporated entities to produce data stored anywhere in the world on valid legal process. This applies regardless of server location, data centre jurisdiction, or contractual protections. A US subsidiary operating an EU data centre is still a US entity.

Sentinel's critical path — interceptor, policy evaluation, trace emission, storage — contains no US-owned components. This is architectural. It is not a configuration switch.

**2. Air-gap operability — does it work with zero network connectivity?**

Classified environments, military networks, and high-security industrial systems often operate with no external network access. A middleware layer that requires a cloud API, a remote policy server, or an external telemetry endpoint cannot be deployed there.

Sentinel uses `FilesystemStorage` as its reference deployment for classified environments. Policy evaluation uses `LocalRegoEvaluator` — OPA runs in-process, no network call. Zero mandatory outbound connections.

**3. Certifiable evidence chain — is it BSI IT-Grundschutz certifiable?**

BSI IT-Grundschutz is the German federal standard for information security, required for government and defence procurement in Germany and applied across EU regulated industries. Certification is a 12–18 month process.

Sentinel is designed with BSI IT-Grundschutz certification as the v3.x target. The BSI profile document is in `docs/bsi-profile.md`.

## What provability means in practice

| Claim | What it requires |
|---|---|
| "EU-operated runtime" | Critical path has no US-owned components |
| "Air-gap capable" | Works with zero network connectivity, tested |
| "BSI certifiable" | Actively pursuing certification, not self-certified |
| "EU AI Act Art. 12 compliant" | Automatic, tamper-resistant, append-only trace |
| "Apache 2.0 permanently" | No CLA that enables relicensing, no BSL switch |

## Privacy by default (v3.2.0+)

Provability without privacy is incoherent. Every trace Sentinel writes
records a SHA-256 ``inputs_hash`` and ``output_hash`` — enough to prove
what was decided and re-verify it against the original data — but the
raw payloads are **not stored by default**.

```python
from sentinel import Sentinel

# Default: hash-only storage. GDPR Art. 25-aligned.
sentinel = Sentinel()
# → trace.inputs  == {}
# → trace.output  == {}
# → trace.inputs_hash  == "<sha256>"
# → trace.output_hash  == "<sha256>"

# Explicit opt-in: raw payloads stored. Only enable when GDPR Art. 6/9
# legal basis is established and trace storage access is controlled.
sentinel = Sentinel(store_inputs=True, store_outputs=True)
```

Two consequences worth naming explicitly:

- **Regulators see proof of logging** (Art. 12 / Art. 13 / Art. 17
  evidence) without Sentinel becoming a second home for personal data.
- **Sentinel cannot reconstruct** what was decided on from its trace
  store alone — which is the correct default when the trace is the
  audit trail, not the source of truth.

Policy evaluators, signers, and in-process observers see the raw
payloads during execution. The privacy redaction is a *storage-boundary*
operation, not an in-flight one. See ``Sentinel._finalise_trace`` in
``sentinel/core/tracer.py`` for the exact point of redaction.

## What we do not claim

- We do not claim that using Sentinel makes your entire system provable. Your IaaS, CI/CD, and development toolchain may still have US dependencies. Sentinel addresses the runtime decision record layer.
- We do not claim BSI certification until it is issued. We say we are pursuing it, and that the architecture is designed to be certifiable.
- We do not claim that Sentinel alone satisfies all EU AI Act obligations. Articles 10, 11, and 15 require organisation-level action.
- We do not claim privacy-by-default prevents you from opting into raw storage. If you pass ``store_inputs=True`` explicitly, your data governance is your own to run.

## Sovereignty as consequence

The three conditions above produce EU sovereignty as an outcome.
The noun Sentinel leads with in public is Provability;
Sovereignty is the consequence you inherit by passing the three
tests. Cylake (US-incorporated) claims *Sovereignty* as its
headline word in the cybersecurity category with billions of
marketing weight; a European open-source project cannot and
should not compete for that word. *Provability* is the
operational thesis; *Record. Enforce. Prove.* is the formula;
and sovereignty follows from both.
