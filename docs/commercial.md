# Commercial support

The `sentinel-kernel` layer is and will remain **Apache 2.0, forever**.
No BSL. No open-core. No paid-only features. No relicensing. That
commitment is architectural — see the three invariants in
[CLAUDE.md](../CLAUDE.md) (no US CLOUD Act exposure in the critical
path, air-gapped must always work, Apache 2.0 forever).

Commercial engagement exists because regulated buyers — banks,
insurers, public-sector IT, KRITIS operators, defence contractors —
need a named, accountable counterparty behind infrastructure they are
about to put in front of an auditor. The open-source layer is the
product. Support is the relationship around it.

---

## The three engagement tiers

### 1 · Self-serve (free, Apache 2.0)

Everything in this repository, forever. Install, integrate, run
`sentinel audit-gap`, ship an evidence pack. The library alone gets
you to roughly the 80 % readiness mark for the EU AI Act Art.
12/13/14/17 technical controls.

**Support:** public GitHub Issues, triaged on a best-effort basis.
**Cost:** zero.
**When this is right:** you have in-house Python and compliance
depth, no hard deadline, no inspection scheduled, no regulator asking
for a named supplier.

### 2 · Design-partner engagement

Structured, fixed-scope engagement with a named deliverable.
Typical engagements:

- **Deployment assistance** — on-premise / air-gapped / VS-NfD-capable
  setup, integration with your SSO, HSM, storage backend, CI.
- **Audit preparation** — review of your trace store, evidence pack,
  manifesto, and policy layer against the specific articles of the
  EU AI Act, DORA, NIS2, or BSI IT-Grundschutz that apply.
- **BSI pre-engagement support** — the pre-engagement package in
  [docs/bsi-pre-engagement/](bsi-pre-engagement/) walked through with
  your SecArch team.
- **Custom policy library** — sector-specific bundles (underwriting,
  clinical, procurement, dual-use) developed against your real
  controls.

**Support:** named point-of-contact, weekly sync, shared issue tracker.
**Scope:** fixed deliverable, fixed price — scoped per engagement.
**When this is right:** you have a deadline, an inspection, or a
specific regulator conversation, and you need a partner through it.

### 3 · Production engagement

SLA-backed support for a production deployment.

- **Response-time SLA** for security advisories and critical bugs
  against a named release line.
- **Incident response** — help investigating a specific decision,
  reconstructing state from traces, preparing the technical portion
  of a regulator-facing incident report.
- **Roadmap co-design** — influence on the next release cycle for
  features blocking your deployment.
- **Security advisory** — private coordinated-disclosure channel.

**Support:** response-time commitments in writing, direct contact,
retainer or time-and-materials.
**Scope:** ongoing, agreed at engagement.
**When this is right:** Sentinel is in your production critical path
and you need contractual accountability around it.

---

## What is explicitly NOT available

- A hosted SaaS version of Sentinel. There is no cloud product, and
  there will not be one. That is the whole point.
- A commercial fork of the core layer with exclusive features. Every
  feature that exists lives in this repository under Apache 2.0.
- Any arrangement that would put US-owned infrastructure in your
  critical path.
- Public pricing tiers. Engagements are scoped individually because
  the scope varies by sector, deployment context, and regulation.

## Supplier

Swentures UG (haftungsbeschränkt), Germany. EU jurisdiction. No CLOUD
Act exposure on the maintainer entity.

Data-processing agreement templates (GDPR Art. 28) available on
request with the design-partner tier.

## How to start

Public, tracked, no marketing follow-up:
**[Open a pilot enquiry on GitHub →](https://github.com/sebastianweiss83/sentinel-kernel/issues/new?labels=pilot&template=pilot_enquiry.md)**

Note in the enquiry if you prefer private follow-up — an email address
in the issue body is sufficient.

Real pricing, real contracts, and a full commercial org will follow
once there are enough design partners to justify them. Until then,
the offer above is handled case by case, transparently, in writing.
