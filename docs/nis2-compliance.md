# NIS2 Compliance Mapping

Directive (EU) 2022/2555 — **Network and Information Security
Directive 2**. Transposition deadline: **17 October 2024**. Member
State law is now in force.

NIS2 applies to essential and important entities in sectors such as
energy, transport, banking, health, digital infrastructure, public
administration, and managed service providers. AI systems used by
these entities for operational decisions fall within scope.

## What Sentinel automates

| Article | Title | Sentinel contribution |
|---|---|---|
| Art. 21 | Cybersecurity risk-management measures | Policy evaluator + kill switch satisfy the measurable-at-runtime components. |
| Art. 23 | Reporting obligations | Append-only decision traces provide the audit substrate for incident reporting. |

## What requires human action

| Article | Title | Why |
|---|---|---|
| Art. 20 | Governance | Board-level cybersecurity accountability is an organisational process, not a software feature. Use the HTML compliance report as board evidence. |
| Art. 24 | European cybersecurity certification schemes | The operator chooses which schemes to adopt (BSI IT-Grundschutz, EUCC, EUCS). See `docs/bsi-profile.md`. |

## How to check

```python
from sentinel import Sentinel
from sentinel.compliance import NIS2Checker

sentinel = Sentinel()
report = NIS2Checker().check(sentinel)
print(report.as_text())
```

Or via CLI:

```bash
sentinel nis2 check
sentinel nis2 check --json
```

## Combined with EU AI Act + DORA

```bash
sentinel compliance check --all-frameworks
sentinel compliance check --critical-infrastructure --html --output nis2.html
```

## Caveats

- NIS2 is transposed differently in each Member State. This
  mapping targets the directive's Article text; national
  transposition may add requirements.
- Sentinel covers the AI-decision layer of a NIS2 deployment.
  Network segmentation, access control, and cryptography are
  operator responsibilities documented in BSI IT-Grundschutz
  Bausteine.
