# ADR-002: Apache 2.0 is permanent

## Status
Accepted

## Context

Open-core and relicensing have become common patterns in
infrastructure software: Elasticsearch, Redis, HashiCorp, MongoDB.
The pattern is usually: Apache 2.0 → Business Source License → rug
pull for users who built on the "free" tier.

Sentinel targets regulated EU industries where:

- Customers need durable legal certainty over what they build on.
- A BSI certification requires a reviewable governance path.
- A relicensing event would invalidate multi-year compliance work.
- Proprietary decision-logging platforms are already in the market;
  the differentiator is irrevocable openness.

## Decision

**Sentinel is Apache 2.0, permanently.**

Specifically:

- No contributor licence agreement (CLA) that would enable the
  founder or any future maintainer to unilaterally relicense the
  codebase.
- No dual-licensing scheme with a "commercial" edition.
- No closed-source enterprise features.
- No feature flags gating "premium" behaviour.
- Any future governance body (e.g. Linux Foundation Europe
  stewardship) inherits this commitment as a condition of joining.

## Consequences

### Positive

- Users can commit to multi-year deployments without rug-pull risk.
- Forks are legitimate and encouraged; the ecosystem is not
  vendor-locked.
- BSI review of the codebase is reviewing the only codebase.
- Fundraising and enterprise monetisation must be built on services
  (support, integration, certification assistance) rather than
  licence gating. This is a constraint, not a bug.

### Negative

- No SaaS upsell through a forced-free tier.
- Monetisation requires building actual services that customers
  choose to pay for, not relying on licence compulsion.

## Alternatives considered

- **AGPL** — rejected. Creates legal ambiguity around "use" and
  scares off some EU enterprise buyers. Apache 2.0 is unambiguous.
- **BSL or SSPL** — rejected. These are the exact patterns Sentinel
  exists to provide an alternative to.
- **Dual-license Apache + commercial** — rejected. Defeats the
  "irrevocable" promise.
