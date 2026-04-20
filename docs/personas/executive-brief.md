# Sentinel — executive brief

*One page. Read in three minutes. Decide whether to assign a pilot.*

## The problem

EU AI Act enforcement starts **2 August 2026**. Every AI decision in a
high-risk use case must be logged automatically, tamper-resistantly,
and produced on demand (Art. 12). Every deployed system needs a
working human-oversight halt (Art. 14). The leading decision-record
platforms are US-owned and expose your audit trail to CLOUD Act
process — unacceptable for banks, insurers, defence, public sector,
and KRITIS operators in the EU.

## The solution

**Sentinel is evidence infrastructure for the regulated AI era.** One
Python decorator on any decision function traces every outcome. A
policy layer enforces every rule. One command produces the signed PDF
evidence pack your auditor accepts. Runs fully offline. Apache 2.0
forever. Under EU jurisdiction.

## The proof

- 📄 [Sample evidence pack (PDF)](../samples/audit-evidence-pack-sample.pdf)
  — open before committing any budget.
- 📋 [Sample `audit-gap` score](../samples/audit-gap-output.txt) — the
  honest readiness split: library-closable, your-decision,
  your-authorship.
- 731+ tests, 100 % line and branch coverage, 40/40 smoke, air-gapped
  CI job.

## The timeline

- **Evaluate (1 week).** Your engineer installs via `pipx`, wraps one
  decision function, produces their first evidence pack. No accounts,
  no keys, no cloud.
- **Pilot (4 weeks).** One regulated decision path in a staging
  environment; deployment pattern validated; audit-prep reviewed with
  the commercial engagement if needed.
- **Production (next quarter).** Storage backend chosen, signing
  keypair generated, trace retention configured, Annex IV document
  authored, evidence pack generated quarterly.

## The cost

- **Self-serve:** zero (Apache 2.0). Your engineer's time.
- **Design-partner engagement:** fixed-price or hourly, scoped at
  engagement time. No public pricing; no per-seat SaaS costs.
- **Production engagement:** SLA-backed; scoped at engagement time.

## The provability argument

The three provability conditions every EU regulated buyer must pass:

1. **Jurisdictional integrity** — is there a US-owned component in
   the critical path? For Sentinel: no.
2. **Air-gap operability** — does it work air-gapped? For Sentinel:
   yes, tested in CI.
3. **Certifiable evidence chain** — is it BSI-certifiable? For
   Sentinel: pre-engagement, actively pursuing IT-Grundschutz
   profile.

US-incorporated competitors fail condition 1 structurally. Sentinel
is the open, jurisdictionally clean alternative. Sovereignty is the
consequence of passing these three conditions — not the headline.

## The next step

Open a pilot enquiry — public, tracked, no marketing follow-up:
[github.com/sebastianweiss83/sentinel-kernel/issues/new?labels=pilot](https://github.com/sebastianweiss83/sentinel-kernel/issues/new?labels=pilot&template=pilot_enquiry.md).

For deeper context: [vision.md](../vision.md) · [roadmap.md](../roadmap.md) · [commercial.md](../commercial.md).
