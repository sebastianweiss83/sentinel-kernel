"""
sentinel.compliance.dora
~~~~~~~~~~~~~~~~~~~~~~~~
EU DORA (Digital Operational Resilience Act) automated compliance checker.

Regulation (EU) 2022/2554. In force since 17 January 2025.

DORA applies to financial entities (banks, insurers, investment
firms, payment institutions, crypto-asset service providers) and
their critical ICT third-party providers. AI systems used by these
entities for decisions that affect customers fall within scope.

What Sentinel automates here:

    Art. 17 — Incident logging and classification
    Art. 6  — ICT risk management framework (partial — policy evaluator)

What requires human action:

    Art. 28 — Third-party contractual arrangements (not a software concern)
    Art. 24 — Digital operational resilience testing (operator process)

The checker explicitly reports the split so no one mistakes
automated coverage for full compliance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


#: DORA has been in force since this date. Unlike the EU AI Act, it
#: is already enforceable. The countdown goes negative.
DORA_ENFORCEMENT_DATE = date(2025, 1, 17)


@dataclass
class DoraArticleReport:
    article: str
    title: str
    status: str  # COMPLIANT | PARTIAL | ACTION_REQUIRED
    automated: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "article": self.article,
            "title": self.title,
            "status": self.status,
            "automated": self.automated,
            "detail": self.detail,
        }


@dataclass
class DoraReport:
    timestamp: datetime
    articles: dict[str, DoraArticleReport] = field(default_factory=dict)

    @property
    def overall(self) -> str:
        if not self.articles:
            return "UNKNOWN"
        statuses = [a.status for a in self.articles.values()]
        if all(s == "COMPLIANT" for s in statuses):
            return "COMPLIANT"
        if any(s == "NON_COMPLIANT" for s in statuses):
            return "NON_COMPLIANT"
        return "PARTIAL"

    @property
    def days_since_enforcement(self) -> int:
        return (date.today() - DORA_ENFORCEMENT_DATE).days

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall": self.overall,
            "days_since_enforcement": self.days_since_enforcement,
            "articles": {k: v.to_dict() for k, v in self.articles.items()},
        }

    def as_text(self) -> str:
        lines = [
            "=" * 64,
            "  DORA COMPLIANCE REPORT",
            f"  Generated: {self.timestamp.isoformat(timespec='seconds')}",
            f"  Days since enforcement (2025-01-17): "
            f"{self.days_since_enforcement}",
            f"  Overall: {self.overall}",
            "=" * 64,
            "",
        ]
        for art in self.articles.values():
            lines.append(f"  {art.article} — {art.title}")
            lines.append(f"    Status: {art.status}")
            lines.append(f"    Detail: {art.detail}")
            lines.append("")
        return "\n".join(lines)


class DoraChecker:
    """
    DORA compliance checker for financial sector AI.

    Usage::

        from sentinel.compliance.dora import DoraChecker

        report = DoraChecker().check(sentinel)
        print(report.overall)
        print(report.as_text())
    """

    def check(self, sentinel: Sentinel) -> DoraReport:
        from sentinel.policy.evaluator import NullPolicyEvaluator

        report = DoraReport(timestamp=datetime.now())

        # Art. 17 — Incident logging (automatable — every trace is a log)
        has_storage = sentinel.storage is not None
        report.articles["Art. 17"] = DoraArticleReport(
            article="Art. 17",
            title="ICT-related incident management, classification and reporting",
            status="COMPLIANT" if has_storage else "NON_COMPLIANT",
            automated=True,
            detail=(
                "Decision traces are append-only and classified by "
                "policy_result — satisfies the incident-log component."
                if has_storage
                else "No storage backend configured."
            ),
        )

        # Art. 6 — ICT risk management framework (partial — policy eval)
        has_policy = not isinstance(sentinel.policy_evaluator, NullPolicyEvaluator)
        report.articles["Art. 6"] = DoraArticleReport(
            article="Art. 6",
            title="ICT risk management framework",
            status="PARTIAL" if has_policy else "ACTION_REQUIRED",
            automated=True,
            detail=(
                "Policy evaluator is configured — risk rules are applied "
                "per decision. Framework documentation remains an "
                "operator responsibility."
                if has_policy
                else "Configure a PolicyEvaluator to apply per-decision risk rules."
            ),
        )

        # Art. 28 — Third-party contractual arrangements (human action)
        report.articles["Art. 28"] = DoraArticleReport(
            article="Art. 28",
            title="ICT third-party risk management",
            status="ACTION_REQUIRED",
            automated=False,
            detail=(
                "Third-party contractual arrangements are out of scope for "
                "Sentinel. Use the sovereignty scanner as input to the "
                "third-party risk register."
            ),
        )

        # Art. 24 — Digital operational resilience testing (human action)
        report.articles["Art. 24"] = DoraArticleReport(
            article="Art. 24",
            title="Digital operational resilience testing",
            status="ACTION_REQUIRED",
            automated=False,
            detail=(
                "Resilience testing (penetration, TLPT) is an operator-driven "
                "process. Sentinel provides the audit trail during tests."
            ),
        )

        return report
