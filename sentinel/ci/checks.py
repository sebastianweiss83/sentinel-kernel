"""
sentinel.ci.checks
~~~~~~~~~~~~~~~~~~
Aggregate CI/CD check orchestrator.

``run_ci_checks`` runs the Sentinel check bundle in-process and
returns a :class:`CICheckResult` with an aggregate exit code. It
wraps these existing library APIs:

    - :class:`sentinel.compliance.euaiact.EUAIActChecker`
    - :class:`sentinel.scanner.runtime.RuntimeScanner`
    - :class:`sentinel.manifesto.SentinelManifesto` (optional)

No subprocesses, no network. Works offline and in air-gapped
environments. Suitable as a single step in a CI pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sentinel.compliance.euaiact import EUAIActChecker
from sentinel.scanner.runtime import RuntimeScanner

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel
    from sentinel.manifesto import SentinelManifesto


PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"


@dataclass
class CICheckOutcome:
    """Result of a single named check."""

    name: str
    status: str  # PASS | FAIL | SKIP
    summary: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "summary": self.summary,
            "detail": self.detail,
        }


@dataclass
class CICheckResult:
    """Aggregated result of a CI check run."""

    outcomes: list[CICheckOutcome] = field(default_factory=list)

    @property
    def overall(self) -> str:
        statuses = [o.status for o in self.outcomes]
        if any(s == FAIL for s in statuses):
            return FAIL
        if any(s == SKIP for s in statuses):
            return "PARTIAL"
        return PASS

    @property
    def exit_code(self) -> int:
        return 1 if self.overall == FAIL else 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "exit_code": self.exit_code,
            "outcomes": [o.to_dict() for o in self.outcomes],
        }

    def as_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    def as_text(self) -> str:
        lines: list[str] = []
        lines.append("=" * 68)
        lines.append("  SENTINEL CI CHECK")
        lines.append("=" * 68)
        for o in self.outcomes:
            lines.append(f"  [{o.status}] {o.name} — {o.summary}")
            if o.detail:
                for extra in o.detail.splitlines():
                    lines.append(f"         {extra}")
        lines.append("-" * 68)
        lines.append(f"  Overall: {self.overall}  (exit {self.exit_code})")
        lines.append("=" * 68)
        return "\n".join(lines)


def run_ci_checks(
    *,
    sentinel: Sentinel | None = None,
    manifesto: SentinelManifesto | None = None,
    repo_root: str = ".",
    scanner: RuntimeScanner | None = None,
    eu_checker: EUAIActChecker | None = None,
) -> CICheckResult:
    """
    Run the Sentinel CI check bundle.

    :param sentinel: a configured Sentinel instance. If omitted, the EU
        AI Act check inspects a None sentinel (which still produces a
        valid report — gaps just show as NOT_CONFIGURED).
    :param manifesto: a SentinelManifesto instance. If omitted, the
        manifesto check is skipped.
    :param repo_root: repository root used by the manifesto check.
    :param scanner: optional :class:`RuntimeScanner` injection for
        tests. Defaults to a fresh scanner.
    :param eu_checker: optional :class:`EUAIActChecker` injection for
        tests. Defaults to a fresh checker.
    :returns: aggregated :class:`CICheckResult`.
    """
    result = CICheckResult()

    # ---- EU AI Act snapshot ---------------------------------------------
    checker = eu_checker if eu_checker is not None else EUAIActChecker()
    eu_report = checker.check(sentinel_instance=sentinel)
    eu_overall = eu_report.overall
    eu_status = PASS if eu_overall != "NON_COMPLIANT" else FAIL
    result.outcomes.append(
        CICheckOutcome(
            name="eu_ai_act",
            status=eu_status,
            summary=f"EU AI Act overall: {eu_overall}",
            detail=(
                f"Automated coverage: {eu_report.automated_coverage:.0%}. "
                "Core articles (12/13/14) must be COMPLIANT."
            ),
        )
    )

    # ---- Runtime sovereignty scan ---------------------------------------
    scan_result = (scanner if scanner is not None else RuntimeScanner()).scan()
    violations = scan_result.critical_path_violations
    if violations:
        result.outcomes.append(
            CICheckOutcome(
                name="sovereignty_scan",
                status=FAIL,
                summary=(
                    f"{len(violations)} critical-path sovereignty violation(s)"
                ),
                detail="\n".join(violations),
            )
        )
    else:
        result.outcomes.append(
            CICheckOutcome(
                name="sovereignty_scan",
                status=PASS,
                summary=(
                    f"{scan_result.total_packages} packages scanned, "
                    "no critical-path violations"
                ),
                detail=(
                    f"Sovereignty score: {scan_result.sovereignty_score:.0%}"
                ),
            )
        )

    # ---- Manifesto (optional) -------------------------------------------
    if manifesto is None:
        result.outcomes.append(
            CICheckOutcome(
                name="manifesto",
                status=SKIP,
                summary="no manifesto provided (pass --manifesto to enable)",
            )
        )
    else:
        m_report = manifesto.check(sentinel=sentinel, repo_root=repo_root)
        hard_gap_count = len(m_report.gaps)
        if hard_gap_count == 0:
            result.outcomes.append(
                CICheckOutcome(
                    name="manifesto",
                    status=PASS,
                    summary=(
                        f"sovereignty score {m_report.overall_score:.0%}, "
                        "no hard gaps"
                    ),
                    detail=(
                        f"Acknowledged gaps: "
                        f"{len(m_report.acknowledged_gaps)}."
                    ),
                )
            )
        else:
            result.outcomes.append(
                CICheckOutcome(
                    name="manifesto",
                    status=FAIL,
                    summary=f"{hard_gap_count} hard manifesto violation(s)",
                    detail="\n".join(
                        f"{g.dimension}: expected {g.expected}, actual {g.actual}"
                        for g in m_report.gaps
                    ),
                )
            )

    return result
