# RFC-001: SovereigntyManifest specification

| Field        | Value                                    |
|--------------|------------------------------------------|
| Status       | ACCEPTED                                 |
| Author       | Sebastian Weiss                          |
| Date         | 2026-04-11                               |
| Comment period | Closed — 14 days elapsed                |
| Implementation | `sentinel/manifesto/base.py` (v1.2.0+)  |

### Implementations

| Language   | Package             | Status                       |
|------------|---------------------|------------------------------|
| Python     | `sentinel-kernel`   | Reference, v2.x stable       |
| Rust       | `sentinel-manifest` | v0.1.0 (`rust-impl/`)        |
| Go         | —                   | Wanted — see issues          |
| TypeScript | —                   | Wanted — see issues          |

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

## Resolved decisions

After the 14-day comment period, the following decisions were made.

1. **Jurisdiction representation — legal entity names.**
   Express jurisdictions using the legal entity name that operates
   the service (`Amazon Web Services, Inc.`, `Mistral AI SAS`),
   not ISO country codes. Rationale: CLOUD Act exposure is a
   property of legal incorporation, not physical location. A
   canonical entity-to-regime mapping is provided in
   `sentinel/scanner/knowledge.py`.

2. **Mixed-jurisdiction deployments — list of jurisdictions.**
   A requirement that accepts multiple jurisdictions uses a list:
   ```python
   jurisdiction = EUOnly(countries=["DE", "FR", "NL"])
   ```
   Parent-child manifesto inheritance is deferred to v2.0 and
   tracked as a separate RFC when there is real demand.

3. **Versioning model — SemVer, embedded in report.**
   Every manifesto report carries a `schema_version` field. See
   ADR-003 for rules: optional fields → no bump, mandatory fields
   or rename → major bump.

4. **Requirement composition — strictest wins.**
   When multiple requirements touch the same dimension, the
   strictest one wins. There is no explicit `inherits` mechanism
   in v1.0.

5. **Acknowledged gap hygiene — mandatory fields.**
   An `AcknowledgedGap` requires **all** of: `provider`,
   `migrating_to`, `by`, and `reason`. An expired `by` date is
   logged as a warning but does not auto-promote to a violation in
   v1.0 — operators retain control of their migration timelines.

6. **Evidence attachment — separate field.**
   A new `evidence` field on every requirement type is reserved
   but not yet used. Actual evidence attachment is deferred to
   v2.0 to allow real-world feedback to shape the mechanism.

7. **TARGETING requirement type — description + by date mandatory.**
   `Targeting(by="2026-Q4")` is the minimum. The description is
   taken from the attribute name (`bsi_certification = Targeting(...)`).

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
