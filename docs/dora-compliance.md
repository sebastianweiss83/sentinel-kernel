# DORA Compliance Mapping

Regulation (EU) 2022/2554 — the **Digital Operational Resilience
Act**. In force for financial entities since **17 January 2025**.

DORA applies to banks, insurers, investment firms, payment
institutions, crypto-asset service providers, and their critical
ICT third-party providers. AI systems used by these entities for
decisions that affect customers fall within scope.

## What Sentinel automates

| Article | Title | Sentinel contribution |
|---|---|---|
| Art. 17 | ICT-related incident management, classification and reporting | Every decision is an append-only, classified trace. Sentinel provides the incident-log substrate. |
| Art. 6  | ICT risk management framework | The policy evaluator applies per-decision risk rules. Framework documentation remains the operator's job. |

## What requires human action

| Article | Title | Why |
|---|---|---|
| Art. 28 | ICT third-party risk management | Contractual arrangements with providers are a procurement and legal concern. Sentinel's sovereignty scanner is the technical input to the third-party risk register, but the register itself is a human process. |
| Art. 24 | Digital operational resilience testing | Penetration testing (TLPT) and scenario-based tests are operator-driven. Sentinel provides the trace log during a test but cannot run it. |

## How to check

```python
from sentinel import Sentinel
from sentinel.compliance import DoraChecker

sentinel = Sentinel()
report = DoraChecker().check(sentinel)

print(f"Overall: {report.overall}")
for art in report.articles.values():
    print(f"  {art.article} — {art.title}: {art.status}")
```

Or via CLI:

```bash
sentinel dora check
sentinel dora check --json
```

## Unified report with EU AI Act + NIS2

```python
from sentinel.compliance import UnifiedComplianceChecker

checker = UnifiedComplianceChecker(
    financial_sector=True,
    critical_infrastructure=True,
)
report = checker.check(sentinel)
report.save_html("full_compliance.html")
```

Or:

```bash
sentinel compliance check --all-frameworks --html --output full.html
```

## Caveats

- DORA's scope is broader than ICT-for-AI. Sentinel addresses the
  AI-decision parts of Art. 17 and Art. 6. It does not replace a
  full DORA compliance programme.
- Third-party risk (Art. 28) is where the sovereignty scanner
  becomes most useful — it enumerates every Python package your
  system depends on and flags CLOUD Act exposure.
- The report is honest about what is automated vs. what requires
  human action. Use the `ACTION_REQUIRED` items as a worksheet.
