# For procurement

You're evaluating whether `sentinel-kernel` can be procured, supported,
and operated inside your organisation.

## Licence

**Apache 2.0, permanently.** No contributor-licence agreement that
enables relicensing. No BSL/SSPL switch in the roadmap. The core
`sentinel-kernel` package will remain Apache 2.0 even if a commercial
edition is ever offered.

See [LICENSE](../../LICENSE) and [GOVERNANCE.md](../../GOVERNANCE.md).

## Supplier

- **Swentures UG (haftungsbeschränkt)**, Germany.
- EU jurisdiction; no CLOUD Act exposure on the maintainer entity.
- Public contact: `sentinel@swentures.com`.

## Commercial support scope

Three tiers, scoped individually (no public pricing):

1. **Self-serve (free, Apache 2.0).** Library, CLI, docs, community
   GitHub Issues. Bug reports triaged.
2. **Design-partner engagement.** Structured scope: deployment
   assistance, custom policy library, integration of your SSO / HSM /
   storage backend, BSI pre-engagement support. Public intake via
   GitHub; private follow-up on request.
3. **Production engagement.** SLA-backed response for production
   incidents, security advisory, audit-preparation hours, roadmap
   co-design. Scoped at engagement time.

Full scope breakdown: [docs/commercial.md](../commercial.md).

## Dependencies / supply-chain posture

- Zero mandatory runtime dependencies. `reportlab` (BSD-3, UK) under
  `[pdf]` extra for the evidence-pack.
- Runtime sovereignty inventory: `sentinel scan --runtime`.
- CI-side sovereignty inventory: `sentinel scan --cicd --repo .`.
- Acknowledged gap: GitHub Actions CI (US-controlled); declared
  migration target is Forgejo.

## Certification posture — honest status

| Claim | Status |
|---|---|
| Apache 2.0 permanently | ✓ current |
| EU AI Act Art. 12/13/14/17 technical controls | ✓ current |
| Air-gapped operation verified | ✓ in CI |
| BSI IT-Grundschutz certification | Pre-engagement (not certified) |
| VS-NfD formal assessment | Pre-engagement (not assessed) |
| ISO 27001 | Not pursued today |
| SOC 2 | Not pursued today |

Roadmap and target dates: [docs/roadmap.md](../roadmap.md).

## Reference customers

No public references at this stage. This will change as
design-partner engagements move to named references; procurement
packs can request current anonymised engagement profiles via the
pilot-enquiry intake.

## Intake

Public, tracked:
[Open a pilot enquiry on GitHub](https://github.com/sebastianweiss83/sentinel-kernel/issues/new?labels=pilot&template=pilot_enquiry.md).
Note in the enquiry if private follow-up is required.

## Data-processing terms

For deployments touching personal data, a data-processing agreement
template is available on request with the design-partner engagement.
Sentinel's default storage model (local SQLite, hash-only) is designed
to minimise processor-role exposure — in the default configuration,
no personal data leaves the deployment environment.
