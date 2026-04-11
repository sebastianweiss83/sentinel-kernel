"""
sentinel.compliance.euaiact
~~~~~~~~~~~~~~~~~~~~~~~~~~~
EU AI Act (Regulation 2024/1689) automated compliance checker.

This checker is explicit about what it can and cannot verify automatically.
Some articles (data governance, technical documentation, accuracy) require
organisation-level action beyond what a middleware kernel can prove. The
report lists those as ``ACTION REQUIRED`` with specific guidance rather
than pretending to check them.
"""

from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel
    from sentinel.manifesto.base import SentinelManifesto


ENFORCEMENT_DATE = date(2026, 8, 2)


@dataclass
class HumanActionItem:
    article: str
    action: str
    guidance: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArticleReport:
    article: str
    title: str
    status: str  # COMPLIANT | PARTIAL | NON_COMPLIANT | ACTION_REQUIRED
    automated: bool
    detail: str
    human_action: HumanActionItem | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.human_action:
            data["human_action"] = self.human_action.to_dict()
        return data


@dataclass
class ComplianceReport:
    timestamp: datetime
    articles: dict[str, ArticleReport] = field(default_factory=dict)
    human_action_required: list[HumanActionItem] = field(default_factory=list)

    @property
    def days_to_enforcement(self) -> int:
        return (ENFORCEMENT_DATE - date.today()).days

    @property
    def automated_coverage(self) -> float:
        if not self.articles:
            return 0.0
        covered = sum(
            1
            for a in self.articles.values()
            if a.automated and a.status == "COMPLIANT"
        )
        return covered / len(self.articles)

    @property
    def overall(self) -> str:
        statuses = [a.status for a in self.articles.values()]
        if not statuses:
            return "UNKNOWN"
        if all(s == "COMPLIANT" for s in statuses):
            return "COMPLIANT"
        if any(s == "NON_COMPLIANT" for s in statuses):
            return "NON_COMPLIANT"
        return "PARTIAL"

    def diff(self) -> str:
        """Human-readable diff — only the gaps."""
        gaps = [
            a for a in self.articles.values()
            if a.status != "COMPLIANT"
        ]
        if not gaps:
            return "No gaps. All automated checks pass."
        lines = ["Gaps between current state and EU AI Act requirements:", ""]
        for a in gaps:
            lines.append(f"  {a.article} — {a.title}: {a.status}")
            lines.append(f"    {a.detail}")
            if a.human_action:
                lines.append(f"    ACTION: {a.human_action.action}")
                lines.append(f"    GUIDANCE: {a.human_action.guidance}")
            lines.append("")
        return "\n".join(lines)

    def as_text(self) -> str:
        lines: list[str] = []
        lines.append("=" * 72)
        lines.append("  EU AI ACT COMPLIANCE REPORT")
        lines.append(f"  Generated: {self.timestamp.isoformat(timespec='seconds')}")
        lines.append(f"  Overall: {self.overall}")
        lines.append(f"  Automated coverage: {self.automated_coverage:.0%}")
        lines.append(f"  Days to enforcement (2 Aug 2026): {self.days_to_enforcement}")
        lines.append("=" * 72)
        lines.append("")
        for art in self.articles.values():
            mark = {
                "COMPLIANT": "OK ",
                "PARTIAL": "PART",
                "NON_COMPLIANT": "FAIL",
                "ACTION_REQUIRED": "TODO",
            }.get(art.status, "?")
            auto = "auto" if art.automated else "manual"
            lines.append(f"  [{mark}] {art.article} ({auto}) — {art.title}")
            lines.append(f"         {art.detail}")
            if art.human_action:
                lines.append(f"         → {art.human_action.action}")
            lines.append("")
        lines.append("=" * 72)
        return "\n".join(lines)

    def as_html(self) -> str:
        def _esc(s: str) -> str:
            return html.escape(s)

        rows = "".join(
            f"<tr>"
            f"<td>{_esc(a.article)}</td>"
            f"<td>{_esc(a.title)}</td>"
            f"<td>{_esc(a.status)}</td>"
            f"<td>{'auto' if a.automated else 'manual'}</td>"
            f"<td>{_esc(a.detail)}</td>"
            f"</tr>"
            for a in self.articles.values()
        )
        action_rows = "".join(
            f"<tr><td>{_esc(h.article)}</td>"
            f"<td>{_esc(h.action)}</td>"
            f"<td>{_esc(h.guidance)}</td></tr>"
            for h in self.human_action_required
        )

        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>EU AI Act Compliance Report</title>
<style>
 body {{ font-family: -apple-system, "Segoe UI", sans-serif; max-width: 1000px;
        margin: 2em auto; color: #111; }}
 h1 {{ font-size: 1.6em; }}
 .overall {{ font-size: 2.5em; font-weight: 700; }}
 .meta {{ color: #555; font-size: 0.9em; }}
 table {{ border-collapse: collapse; width: 100%; margin-top: .6em; }}
 th, td {{ border: 1px solid #ddd; padding: .4em .6em; text-align: left; font-size: .92em; }}
 th {{ background: #f4f4f4; }}
</style>
</head>
<body>
<h1>EU AI Act Compliance Report</h1>
<p class="meta">Generated: {self.timestamp.isoformat(timespec='seconds')}<br>
Days to enforcement (2 Aug 2026): {self.days_to_enforcement}<br>
Automated coverage: {self.automated_coverage:.0%}</p>
<div class="overall">{self.overall}</div>

<h2>Per-article status</h2>
<table><thead><tr>
 <th>Article</th><th>Title</th><th>Status</th><th>Coverage</th><th>Detail</th>
</tr></thead><tbody>{rows}</tbody></table>

<h2>Human action items</h2>
<table><thead><tr>
 <th>Article</th><th>Action</th><th>Guidance</th>
</tr></thead><tbody>{action_rows or '<tr><td colspan="3">None</td></tr>'}</tbody></table>
</body>
</html>
"""

    def as_json(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall": self.overall,
            "automated_coverage": round(self.automated_coverage, 3),
            "days_to_enforcement": self.days_to_enforcement,
            "articles": {k: v.to_dict() for k, v in self.articles.items()},
            "human_action_required": [h.to_dict() for h in self.human_action_required],
        }

    def export_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.as_json(), indent=2), encoding="utf-8")


class EUAIActChecker:
    """
    Automated compliance checker for the EU AI Act.

    Usage::

        checker = EUAIActChecker()
        report = checker.check(sentinel_instance)
        print(report.diff())
    """

    ENFORCEMENT_DATE = ENFORCEMENT_DATE

    def check(
        self,
        sentinel_instance: Sentinel | None = None,
        manifesto: SentinelManifesto | None = None,
    ) -> ComplianceReport:
        from sentinel.policy.evaluator import NullPolicyEvaluator

        report = ComplianceReport(timestamp=datetime.now())

        has_policy = (
            sentinel_instance is not None
            and not isinstance(sentinel_instance.policy_evaluator, NullPolicyEvaluator)
        )
        has_kill_switch = (
            sentinel_instance is not None
            and hasattr(sentinel_instance, "engage_kill_switch")
            and hasattr(sentinel_instance, "disengage_kill_switch")
        )
        has_storage = sentinel_instance is not None and sentinel_instance.storage is not None

        # ----- Art. 9 — Risk management (PARTIAL) ---------------------------
        if has_policy:
            art9 = ArticleReport(
                article="Art. 9",
                title="Risk management",
                status="PARTIAL",
                automated=True,
                detail="Policy evaluator configured; every decision records the policy result.",
                human_action=HumanActionItem(
                    article="Art. 9",
                    action="Document your risk management procedure",
                    guidance="Art. 9 requires a documented, ongoing risk assessment. The trace record alone is not sufficient — a risk management plan must exist.",
                ),
            )
        else:
            art9 = ArticleReport(
                article="Art. 9",
                title="Risk management",
                status="NON_COMPLIANT",
                automated=True,
                detail="No policy evaluator wired up — decisions not being evaluated against rules.",
                human_action=HumanActionItem(
                    article="Art. 9",
                    action="Configure a PolicyEvaluator on Sentinel",
                    guidance="Use SimpleRuleEvaluator or LocalRegoEvaluator. Pass via Sentinel(policy_evaluator=...).",
                ),
            )
        report.articles["Art. 9"] = art9

        # ----- Art. 10 — Data governance (NOT AUTOMATABLE) ------------------
        art10 = ArticleReport(
            article="Art. 10",
            title="Data governance",
            status="ACTION_REQUIRED",
            automated=False,
            detail="Data governance is not automatable by a middleware kernel.",
            human_action=HumanActionItem(
                article="Art. 10",
                action="Document your training/evaluation data provenance, quality, and bias mitigation",
                guidance="Keep datasheets. Version datasets. Record pre-processing steps. These are organisational, not runtime.",
            ),
        )
        report.articles["Art. 10"] = art10

        # ----- Art. 11 — Technical documentation (NOT AUTOMATABLE) ----------
        art11 = ArticleReport(
            article="Art. 11",
            title="Technical documentation",
            status="ACTION_REQUIRED",
            automated=False,
            detail="Annex IV technical documentation is a human deliverable.",
            human_action=HumanActionItem(
                article="Art. 11",
                action="Prepare Annex IV technical documentation",
                guidance="System description, architecture, training methodology, metrics, risk management outcomes, post-market plan.",
            ),
        )
        report.articles["Art. 11"] = art11

        # ----- Art. 12 — Automatic logging (COMPLIANT if storage wired) -----
        art12 = ArticleReport(
            article="Art. 12",
            title="Automatic record keeping",
            status="COMPLIANT" if has_storage else "NON_COMPLIANT",
            automated=True,
            detail=(
                "Every wrapped call produces a DecisionTrace automatically, stored append-only."
                if has_storage
                else "No storage backend configured."
            ),
        )
        report.articles["Art. 12"] = art12

        # ----- Art. 13 — Transparency to deployers (COMPLIANT) --------------
        art13 = ArticleReport(
            article="Art. 13",
            title="Transparency & information to deployers",
            status="COMPLIANT" if has_storage else "NON_COMPLIANT",
            automated=True,
            detail="Traces record agent, model, policy name/version, and result per decision.",
        )
        report.articles["Art. 13"] = art13

        # ----- Art. 14 — Human oversight (COMPLIANT if kill switch) ---------
        if has_kill_switch:
            art14 = ArticleReport(
                article="Art. 14",
                title="Human oversight",
                status="COMPLIANT",
                automated=True,
                detail="Kill switch implemented; every override recorded as linked trace entry.",
                human_action=HumanActionItem(
                    article="Art. 14",
                    action="Define who operates the kill switch",
                    guidance="Runtime halt is only half the story — a named human must have the authority and procedure to engage it.",
                ),
            )
        else:
            art14 = ArticleReport(
                article="Art. 14",
                title="Human oversight",
                status="NON_COMPLIANT",
                automated=True,
                detail="No kill switch on this Sentinel instance.",
                human_action=HumanActionItem(
                    article="Art. 14",
                    action="Upgrade sentinel-kernel to >=0.4.0",
                    guidance="Kill switch shipped in v0.1.1. Call sentinel.engage_kill_switch(reason) to halt.",
                ),
            )
        report.articles["Art. 14"] = art14

        # ----- Art. 15 — Accuracy, robustness, cybersecurity ----------------
        art15 = ArticleReport(
            article="Art. 15",
            title="Accuracy, robustness, cybersecurity",
            status="ACTION_REQUIRED",
            automated=False,
            detail="Model evaluation and adversarial testing are outside the trace layer.",
            human_action=HumanActionItem(
                article="Art. 15",
                action="Run model evaluation suite and penetration tests",
                guidance="Accuracy benchmarks on held-out data. Adversarial robustness. Cyber hardening of the serving stack.",
            ),
        )
        report.articles["Art. 15"] = art15

        # ----- Art. 17 — Quality management (COMPLIANT if storage) ----------
        art17 = ArticleReport(
            article="Art. 17",
            title="Quality management system",
            status="COMPLIANT" if has_storage else "NON_COMPLIANT",
            automated=True,
            detail="Continuous, append-only trace record satisfies the traceability requirement.",
            human_action=HumanActionItem(
                article="Art. 17",
                action="Document the full QMS — not only traceability",
                guidance="Art. 17 requires change control, incident management, and supplier controls in addition to traceability.",
            ),
        )
        report.articles["Art. 17"] = art17

        report.human_action_required = [
            a.human_action
            for a in report.articles.values()
            if a.human_action is not None
        ]
        return report
