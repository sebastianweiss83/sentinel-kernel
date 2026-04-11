# RFC-001: SovereigntyManifest specification

| Field        | Value                                    |
|--------------|------------------------------------------|
| Status       | DRAFT                                    |
| Author       | Sebastian Weiss                          |
| Date         | 2026-04-11                               |
| Comment period | 14 days once opened as GitHub Discussion |

---

## Summary

A machine-readable specification for expressing and verifying
sovereignty requirements in AI systems.

Organisations deploying AI under the EU AI Act and the EU sovereignty
agenda need to express their constraints in a form that (a) a
machine can check against reality and (b) a human auditor can read
without running the code.

This RFC defines that form.

---

## Motivation

Today, sovereignty requirements live in PowerPoint decks and Excel
spreadsheets. Procurement teams negotiate them, legal teams approve
them, and engineering teams are expected to honour them by hand.

The gap between the declared policy and the running system is where
incidents happen. A `SovereigntyManifest` closes that gap: it is the
policy, and it is simultaneously the check that runs in CI.

Secondary motivations:

- **Portability.** The specification should work for any sovereign
  AI project — not just Sentinel. A Haystack-based stack, a KServe
  deployment, and a custom agent pipeline should all be able to
  declare a manifest in the same vocabulary.
- **Honest gap reporting.** Every manifesto check produces a
  distinction between *violations* (unacknowledged gaps) and
  *acknowledged gaps with migration plans*. Procurement wants the
  difference in writing.
- **Audit evidence.** The output of a manifesto check is structured
  JSON that can be signed, archived, and cited by a regulator.

---

## Proposed specification

### Core concepts

A manifesto is a class that declares *requirements* as attributes.
Each requirement is one of a fixed set of types. The manifesto
runtime evaluates the requirements against reality and returns a
structured report.

```python
from sentinel.manifesto import (
    SentinelManifesto,
    EUOnly,
    OnPremiseOnly,
    Required,
    ZeroExposure,
    Targeting,
    AcknowledgedGap,
)

class OurPolicy(SentinelManifesto):
    jurisdiction  = EUOnly()
    cloud_act     = ZeroExposure()
    kill_switch   = Required()
    storage       = OnPremiseOnly(country="DE")
    bsi           = Targeting(by="2026-12-31")

    # Explicit, documented, time-bound gap
    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Forgejo self-hosted",
        by="2027-Q2",
        reason="No EU-sovereign alternative with comparable UX yet",
    )

report = OurPolicy().check()
report.export_json("sovereignty_report.json")
```

### Requirement types (v0.9)

| Type                   | Semantics                                        |
|------------------------|--------------------------------------------------|
| `EUOnly()`             | No US-owned packages in runtime critical path.  |
| `OnPremiseOnly(country)`| Storage backend must be local/on-premise.       |
| `Required()`           | Named capability must be present at runtime.    |
| `ZeroExposure()`       | Zero CLOUD Act exposure in runtime, CI/CD, infra.|
| `Targeting(by)`        | Statement of intent with deadline (non-gating). |
| `AcknowledgedGap(...)` | Known gap with documented migration plan.       |

### Report shape

```json
{
  "timestamp": "2026-04-11T10:00:00",
  "overall_score": 0.83,
  "days_to_enforcement": 113,
  "sovereignty_dimensions": {
    "jurisdiction": {
      "name": "jurisdiction",
      "expected": "No US-owned packages in runtime critical path",
      "satisfied": true,
      "detail": "0 critical-path violations"
    }
  },
  "eu_ai_act_articles": {
    "Art. 12": "COMPLIANT (traces written)",
    "Art. 14": "COMPLIANT (kill switch implemented)"
  },
  "gaps": [...],
  "acknowledged_gaps": [...],
  "migration_plans": [...]
}
```

### Adoption path

1. **v0.9 (this RFC)** — Sentinel implements the specification as
   `sentinel.manifesto.SentinelManifesto`. Other projects can copy
   the schema and produce compatible reports.
2. **v1.0** — Freeze the JSON schema as `sovereignty-manifest/v1`.
   Publish the JSON Schema file under `docs/schemas/`.
3. **Beyond v1.0** — Graduate the specification to a Linux
   Foundation Europe working group. Invite adjacent projects
   (observability, agent frameworks, policy engines) to adopt it.

---

## Open questions

These are the points where input from design partners, BSI, and
legal counsel will shape the final design.

1. **Jurisdiction representation.**
   Express jurisdictions as ISO-3166 country codes (`DE`, `FR`,
   `US`), as legal entities (`Amazon Web Services EMEA SARL`), or as
   named regulatory regimes (`CLOUD_ACT`, `GDPR_EU`)? Each has
   tradeoffs. Probably all three, with a canonical mapping.

2. **Mixed-jurisdiction deployments.**
   A multi-national hospital chain may legitimately operate under
   different rules in different countries. How does the manifesto
   express "EU-only in DE, cloud OK in NL"? Per-subsystem manifests
   with a parent-child relationship?

3. **Versioning model.**
   The manifest schema must be versioned. `manifest_version: "1.0"`
   at the top? SemVer? Year-based? A version negotiation during a
   multi-project audit is fine, but we need one canonical rule.

4. **Requirement composition.**
   How do requirements compose when multiple manifests apply? Union
   (strictest wins)? Named overrides? Explicit `inherits` clause?

5. **Acknowledged gap hygiene.**
   An `AcknowledgedGap` with an expired `by` date should become a
   violation. The check needs a policy for "grace period" and
   "immediate demotion" — which should be configurable but with a
   safe default.

6. **Evidence attachment.**
   Should the manifest carry links to supporting evidence (SoC 2
   report, BSI assessment, penetration test summary)? This would
   make the manifesto the single document a regulator consumes.

---

## Rationale for this approach

- **Plain Python class.** No YAML DSL to learn, no parser to debug.
  The class is the document. Editors, linters, and type checkers
  already work.
- **Fixed vocabulary.** The requirement types are a closed set so
  that cross-project comparisons are meaningful. Adding a new type
  requires an RFC.
- **Machine-checkable.** Running the manifest against reality is one
  function call. The output is JSON, so it integrates into CI,
  dashboards, and regulatory submissions without glue.
- **Honest about gaps.** Every non-sovereign project has gaps today.
  Pretending otherwise damages trust. `AcknowledgedGap` is a
  first-class concept.

---

## Alternatives considered

- **YAML / TOML manifest.** Rejected because the check logic has to
  live somewhere — a YAML file needs a separate interpreter, which
  is the same problem pushed one layer down.
- **OPA / Rego.** Rejected for the manifest layer (still endorsed
  for per-decision policy evaluation) because the semantics of
  "this installed package is a CLOUD Act violation" are not a good
  fit for Rego's declarative pattern.
- **JSON Schema alone.** Rejected because a schema can express the
  shape but cannot express the verification. We need both.

---

## Implementation status

- `sentinel/manifesto/base.py` — v1.0 reference implementation.
- `examples/10_manifesto.py` — runnable example with a realistic
  manifest declaration, `EUOnly` / `Required` / `AcknowledgedGap`
  requirement mix, and JSON export.
- `tests/test_manifesto.py` + `tests/test_manifesto_extra.py` —
  36 tests covering every requirement type, EU AI Act checks, JSON
  and HTML export, and every branch of the check engine.

---

## Call for feedback

Input welcome from:

- **BSI** — does this shape fit the IT-Grundschutz evidence expectations?
- **Design partners** — do the requirement types cover your deployment?
- **Adjacent projects** — would you adopt the schema if it were stable?
- **Legal counsel** — does "acknowledged gap" hold up as a legal concept?

Open a GitHub Discussion on this repo to comment. Discussion period:
14 days from the public announcement of this RFC.
