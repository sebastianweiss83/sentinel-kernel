# RFC-001 — Python implementation reference

This document maps the RFC-001 specification onto the concrete
Python implementation in `sentinel.manifesto`.

| Status | ACCEPTED and implemented in sentinel-kernel ≥ v1.2.0 |
|---|---|

## How the spec maps to code

| RFC concept | Python class | Source |
|---|---|---|
| Manifesto | `SentinelManifesto` | `sentinel/manifesto/base.py` |
| EUOnly requirement | `EUOnly` | `sentinel/manifesto/base.py` |
| OnPremiseOnly | `OnPremiseOnly` | `sentinel/manifesto/base.py` |
| Required capability | `Required` | `sentinel/manifesto/base.py` |
| ZeroExposure | `ZeroExposure` | `sentinel/manifesto/base.py` |
| Targeting | `Targeting` | `sentinel/manifesto/base.py` |
| AcknowledgedGap | `AcknowledgedGap` | `sentinel/manifesto/base.py` |
| GDPRCompliant (v1.2) | `GDPRCompliant` | `sentinel/manifesto/base.py` |
| RetentionPolicy (v1.2) | `RetentionPolicy` | `sentinel/manifesto/base.py` |
| AuditTrailIntegrity (v1.2) | `AuditTrailIntegrity` | `sentinel/manifesto/base.py` |
| BSIProfile (v1.2) | `BSIProfile` | `sentinel/manifesto/base.py` |
| Manifesto report | `ManifestoReport` | `sentinel/manifesto/base.py` |
| Report JSON export | `ManifestoReport.as_json()` | `sentinel/manifesto/base.py` |
| Report HTML export | `ManifestoReport.as_html()` | `sentinel/manifesto/base.py` |

## Minimal example

```python
from sentinel.manifesto import (
    SentinelManifesto,
    EUOnly,
    Required,
    AcknowledgedGap,
    BSIProfile,
)

class OurPolicy(SentinelManifesto):
    jurisdiction = EUOnly()
    kill_switch  = Required()
    bsi          = BSIProfile(
        status="pursuing",
        by="2026-Q4",
        evidence="docs/bsi-profile.md",
    )
    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No EU-sovereign CI with comparable UX yet",
    )

from sentinel import Sentinel
sentinel = Sentinel()

report = OurPolicy().check(sentinel=sentinel)
print(f"Overall: {report.overall_score:.0%}")
for name, dim in report.sovereignty_dimensions.items():
    mark = "OK" if dim.satisfied else "GAP"
    print(f"  [{mark}] {name}: {dim.detail}")
```

## Report schema (illustrative)

```json
{
  "timestamp": "2026-04-11T13:30:00",
  "overall_score": 0.83,
  "days_to_enforcement": 113,
  "sovereignty_dimensions": {
    "jurisdiction": {
      "name": "jurisdiction",
      "expected": "No US-owned packages in runtime critical path",
      "satisfied": true,
      "detail": "0 critical-path violations"
    },
    "bsi": {
      "name": "bsi",
      "expected": "BSI pursuing by 2026-Q4",
      "satisfied": true,
      "detail": "status=pursuing evidence=docs/bsi-profile.md (present)"
    }
  },
  "eu_ai_act_articles": {
    "Art. 12": "COMPLIANT (traces written)",
    "Art. 14": "COMPLIANT (kill switch implemented)"
  },
  "gaps": [],
  "acknowledged_gaps": [
    {
      "kind": "acknowledged_gap",
      "provider": "GitHub Actions",
      "migrating_to": "Self-hosted Forgejo",
      "by": "2027-Q2",
      "reason": "No EU-sovereign CI with comparable UX yet"
    }
  ],
  "migration_plans": [...]
}
```

## Tests

- `tests/test_manifesto.py` — core requirement coverage, v1.0 types
- `tests/test_manifesto.py` — v1.2 types (GDPR, retention, audit, BSI)
- `tests/test_rfc001_compliance.py` — validates a real manifesto
  against the RFC-001 report shape

## Third-party implementations

A Rust port of `SovereigntyManifest` following RFC-001 is tracked
as a good-first-issue (#13). The target schema version is
`sovereignty-manifest/v1`, identical to the Python implementation.
