# What sovereignty means

Open source is not the same as sovereign.

A library can be Apache 2.0 and still route your data through US infrastructure. A self-hosted tool can run on EU servers operated by a US company — still subject to US CLOUD Act. Sovereignty is a property of the runtime, not just the code.

## The three tests

**1. Jurisdiction: is there a US-owned component in the critical path?**

The US CLOUD Act (18 U.S.C. § 2713) requires US-incorporated entities to produce data stored anywhere in the world on valid legal process. This applies regardless of server location, data centre jurisdiction, or contractual protections. A US subsidiary operating an EU data centre is still a US entity.

Sentinel's critical path — interceptor, policy evaluation, trace emission, storage — contains no US-owned components. This is architectural. It is not a configuration switch.

**2. Air-gap: does it work with zero network connectivity?**

Classified environments, military networks, and high-security industrial systems often operate with no external network access. A middleware layer that requires a cloud API, a remote policy server, or an external telemetry endpoint cannot be deployed there.

Sentinel uses `FilesystemStorage` as its reference deployment for classified environments. Policy evaluation uses `LocalRegoEvaluator` — OPA runs in-process, no network call. Zero mandatory outbound connections.

**3. Certification: is it BSI IT-Grundschutz certifiable?**

BSI IT-Grundschutz is the German federal standard for information security, required for government and defence procurement in Germany and applied across EU regulated industries. Certification is a 12–18 month process.

Sentinel is designed with BSI IT-Grundschutz certification as the v1.0 target. The BSI profile document is in `docs/bsi-profile.md`.

## What sovereign means in practice

| Claim | What it requires |
|---|---|
| "EU-sovereign runtime" | Critical path has no US-owned components |
| "Air-gapped capable" | Works with zero network connectivity, tested |
| "BSI certifiable" | Actively pursuing certification, not self-certified |
| "EU AI Act Art. 12 compliant" | Automatic, tamper-resistant, append-only trace |
| "Apache 2.0 permanently" | No CLA that enables relicensing, no BSL switch |

## What we do not claim

- We do not claim that using Sentinel makes your entire system sovereign. Your IaaS, CI/CD, and development toolchain may still have US dependencies. Sentinel addresses the runtime decision record layer.
- We do not claim BSI certification until it is issued. We say we are pursuing it, and that the architecture is designed to be certifiable.
- We do not claim that Sentinel alone satisfies all EU AI Act obligations. Articles 10, 11, and 15 require organisation-level action.
