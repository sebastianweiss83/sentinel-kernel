"""
sentinel.compliance.unified
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unified compliance checker that runs EU AI Act, DORA, and NIS2
in one command.

Usage::

    from sentinel.compliance import UnifiedComplianceChecker

    checker = UnifiedComplianceChecker(
        financial_sector=True,        # run DORA
        critical_infrastructure=True, # run NIS2
    )
    report = checker.check(sentinel)
    print(report.as_text())
    report.save_html("full_compliance.html")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sentinel.compliance.dora import DoraChecker, DoraReport
from sentinel.compliance.euaiact import ComplianceReport, EUAIActChecker
from sentinel.compliance.nis2 import NIS2Checker, NIS2Report

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


@dataclass
class UnifiedReport:
    timestamp: datetime
    eu_ai_act: ComplianceReport
    dora: DoraReport | None = None
    nis2: NIS2Report | None = None
    frameworks: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "timestamp": self.timestamp.isoformat(),
            "frameworks": self.frameworks,
            "eu_ai_act": self.eu_ai_act.as_json(),
        }
        if self.dora is not None:
            out["dora"] = self.dora.as_dict()
        if self.nis2 is not None:
            out["nis2"] = self.nis2.as_dict()
        return out

    def as_text(self) -> str:
        parts = [self.eu_ai_act.as_text()]
        if self.dora is not None:
            parts.append(self.dora.as_text())
        if self.nis2 is not None:
            parts.append(self.nis2.as_text())
        return "\n".join(parts)

    def save_html(self, path: str | Path) -> None:
        """Emit a minimal self-contained HTML summary.

        The rich HTML compliance report lives in the dashboard
        module. This is the quick unified summary.
        """
        body = self._render_html()
        Path(path).write_text(body, encoding="utf-8")

    def _render_html(self) -> str:
        sections: list[str] = [
            "<!doctype html>",
            "<html lang='en'><head><meta charset='utf-8'>",
            "<title>Sentinel unified compliance report</title>",
            "<style>body{font-family:system-ui,sans-serif;max-width:900px;"
            "margin:2rem auto;padding:0 1.5rem;background:#0a0e14;color:#e5e7eb;}"
            "h1{border-bottom:2px solid #00d084;padding-bottom:.3em;}"
            "h2{margin-top:2em;border-bottom:1px solid #1f2937;padding-bottom:.2em;}"
            "pre{background:#111827;padding:1rem;border-radius:6px;overflow-x:auto;"
            "font-family:ui-monospace,monospace;font-size:.9rem;}"
            "</style></head><body>",
            "<h1>Sentinel unified compliance report</h1>",
            f"<p>Generated: {self.timestamp.isoformat(timespec='seconds')}</p>",
            f"<p>Frameworks checked: {', '.join(self.frameworks)}</p>",
            "<h2>EU AI Act</h2>",
            f"<pre>{_escape(self.eu_ai_act.as_text())}</pre>",
        ]
        if self.dora is not None:
            sections += ["<h2>DORA</h2>", f"<pre>{_escape(self.dora.as_text())}</pre>"]
        if self.nis2 is not None:
            sections += ["<h2>NIS2</h2>", f"<pre>{_escape(self.nis2.as_text())}</pre>"]
        sections += ["</body></html>"]
        return "\n".join(sections)


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


class UnifiedComplianceChecker:
    """
    Run every applicable compliance check in one command.

    Detects which frameworks apply based on the caller's context:

      - EU AI Act  — always
      - DORA       — when financial_sector=True
      - NIS2       — when critical_infrastructure=True
    """

    def __init__(
        self,
        *,
        financial_sector: bool = False,
        critical_infrastructure: bool = False,
    ) -> None:
        self.financial_sector = financial_sector
        self.critical_infrastructure = critical_infrastructure

    def check(self, sentinel: Sentinel) -> UnifiedReport:
        eu = EUAIActChecker().check(sentinel)
        frameworks = ["EU AI Act"]

        dora = None
        if self.financial_sector:
            dora = DoraChecker().check(sentinel)
            frameworks.append("DORA")

        nis2 = None
        if self.critical_infrastructure:
            nis2 = NIS2Checker().check(sentinel)
            frameworks.append("NIS2")

        return UnifiedReport(
            timestamp=datetime.now(),
            eu_ai_act=eu,
            dora=dora,
            nis2=nis2,
            frameworks=frameworks,
        )
