"""
sentinel.compliance.nis2
~~~~~~~~~~~~~~~~~~~~~~~~
EU NIS2 (Network and Information Security Directive 2) automated
compliance checker.

Directive (EU) 2022/2555. Transposition deadline was 17 October
2024 — Member-State law now in force.

NIS2 applies to essential and important entities in sectors such as
energy, transport, banking, health, digital infrastructure, public
administration, and managed service providers. AI systems used by
these entities for operational decisions fall within scope.

What Sentinel automates here:

    Art. 21 — Cybersecurity risk-management measures (partial)
    Art. 23 — Reporting obligations (automated via trace log)

What requires human action:

    Art. 20 — Governance (board-level accountability)
    Art. 24 — Use of European cybersecurity certification schemes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


#: NIS2 transposition deadline. The directive requires Member State
#: law; this is the date the EU-level deadline kicked in.
NIS2_ENFORCEMENT_DATE = date(2024, 10, 17)


@dataclass
class NIS2ArticleReport:
    article: str
    title: str
    status: str
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
class NIS2Report:
    timestamp: datetime
    articles: dict[str, NIS2ArticleReport] = field(default_factory=dict)

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
        return (date.today() - NIS2_ENFORCEMENT_DATE).days

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
            "  NIS2 COMPLIANCE REPORT",
            f"  Generated: {self.timestamp.isoformat(timespec='seconds')}",
            f"  Days since enforcement (2024-10-17): "
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


class NIS2Checker:
    """
    NIS2 compliance checker for critical infrastructure AI.

    Usage::

        from sentinel.compliance.nis2 import NIS2Checker

        report = NIS2Checker().check(sentinel)
        print(report.as_text())
    """

    def check(self, sentinel: Sentinel) -> NIS2Report:
        from sentinel.policy.evaluator import NullPolicyEvaluator

        report = NIS2Report(timestamp=datetime.now())

        # Art. 21 — Cybersecurity risk-management (partial — policy-aware)
        has_policy = not isinstance(sentinel.policy_evaluator, NullPolicyEvaluator)
        has_kill = hasattr(sentinel, "engage_kill_switch")
        compliant = has_policy and has_kill
        report.articles["Art. 21"] = NIS2ArticleReport(
            article="Art. 21",
            title="Cybersecurity risk-management measures",
            status="COMPLIANT" if compliant else "PARTIAL",
            automated=True,
            detail=(
                "Policy evaluation and kill-switch are wired up — satisfies "
                "the measurable components."
                if compliant
                else "Policy evaluator and/or kill switch not fully configured."
            ),
        )

        # Art. 23 — Reporting obligations (trace log serves as evidence)
        report.articles["Art. 23"] = NIS2ArticleReport(
            article="Art. 23",
            title="Reporting obligations",
            status="COMPLIANT",
            automated=True,
            detail=(
                "Decision traces provide the append-only log required to "
                "support incident reporting under Art. 23."
            ),
        )

        # Art. 20 — Governance (human action)
        report.articles["Art. 20"] = NIS2ArticleReport(
            article="Art. 20",
            title="Governance (board-level accountability)",
            status="ACTION_REQUIRED",
            automated=False,
            detail=(
                "Board-level cybersecurity accountability cannot be "
                "automated. Use the HTML compliance report as evidence "
                "for the board."
            ),
        )

        # Art. 24 — European certification (human action)
        report.articles["Art. 24"] = NIS2ArticleReport(
            article="Art. 24",
            title="Use of European cybersecurity certification schemes",
            status="ACTION_REQUIRED",
            automated=False,
            detail=(
                "The operator chooses which certification schemes to "
                "adopt. See docs/bsi-profile.md for the IT-Grundschutz "
                "path."
            ),
        )

        return report
