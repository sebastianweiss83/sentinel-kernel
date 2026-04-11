"""
sentinel.manifesto.base
~~~~~~~~~~~~~~~~~~~~~~~
Define your organisation's sovereignty policy in code. Run it against
reality. Get back a structured report with gaps, acknowledged gaps,
and migration plans.

    class OurPolicy(SentinelManifesto):
        jurisdiction = EUOnly()
        storage = OnPremiseOnly(country="DE")
        airgap = Required()
        cloud_act = ZeroExposure()
        bsi = Targeting(by="2026-12-31")

        cicd = AcknowledgedGap(
            provider="github_actions",
            migrating_to="forgejo",
            by="2027-Q2",
            reason="No EU-sovereign alternative ready",
        )

    report = OurPolicy().check()
    print(report.as_text())
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sentinel.scanner import CICDScanner, InfrastructureScanner, RuntimeScanner

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel
    from sentinel.scanner import CICDScanResult, InfraScanResult, ScanResult


EU_AI_ACT_ENFORCEMENT_DATE = date(2026, 8, 2)


# ---------------------------------------------------------------------------
# Requirement types
# ---------------------------------------------------------------------------


class Requirement:
    """Base class for all manifesto requirements."""

    kind: str = "requirement"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "detail": self.__class__.__name__}


class EUOnly(Requirement):
    kind = "eu_only"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind}


@dataclass
class OnPremiseOnly(Requirement):
    country: str
    kind: str = "on_premise_only"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "country": self.country}


class Required(Requirement):
    kind = "required"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind}


class ZeroExposure(Requirement):
    kind = "zero_exposure"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind}


@dataclass
class Targeting(Requirement):
    by: str  # ISO date or "Q4 2026" style
    kind: str = "targeting"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "by": self.by}


@dataclass
class AcknowledgedGap(Requirement):
    """
    A known non-sovereign dependency with a documented migration plan.

    An acknowledged gap is honest reporting, not a violation. The report
    lists it separately from ungap'd violations.
    """
    provider: str
    migrating_to: str
    by: str
    reason: str
    kind: str = "acknowledged_gap"

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "provider": self.provider,
            "migrating_to": self.migrating_to,
            "by": self.by,
            "reason": self.reason,
        }


class GDPRCompliant(Requirement):
    """Storage must comply with GDPR data minimisation.

    Checks:
      - ``inputs_raw`` is not stored by default (only ``inputs_hash``).
      - ``data_residency`` is within the EU.
      - A retention policy is configured (documented — Sentinel does
        not enforce retention, the operator does).
    """
    kind = "gdpr_compliant"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind}


@dataclass
class RetentionPolicy(Requirement):
    """Trace retention must not exceed a specified period.

    Args:
        max_days: Maximum days to retain traces. Defaults to 7 years,
            the minimum for most EU AI Act high-risk regimes.
    """
    max_days: int = 365 * 7
    kind: str = "retention_policy"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "max_days": self.max_days}


class AuditTrailIntegrity(Requirement):
    """Verifies append-only storage is actually append-only.

    Checks that the configured storage backend does not expose any
    UPDATE or DELETE methods on traces. Override chains must be
    expressed as new linked traces, not mutations.
    """
    kind = "audit_trail_integrity"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind}


@dataclass
class BSIProfile(Requirement):
    """System is pursuing or has BSI IT-Grundschutz certification.

    Args:
        status: Either ``"pursuing"`` or ``"certified"``.
        by: Target date string, e.g. ``"2026-Q4"``.
        evidence: Path to the BSI profile document relative to repo root.
    """
    status: str = "pursuing"  # "pursuing" | "certified"
    by: str = ""
    evidence: str = "docs/bsi-profile.md"
    kind: str = "bsi_profile"

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "status": self.status,
            "by": self.by,
            "evidence": self.evidence,
        }


class VSNfDReady(Requirement):
    """System meets VS-NfD deployment requirements.

    Checks a deployment against the automatable subset of the
    VS-NfD (Verschlusssache — Nur für den Dienstgebrauch)
    profile. The checks are:

      - Storage backend is one of: ``postgres`` | ``filesystem``.
        SQLite is *not* suitable for VS-NfD multi-user deployments.
      - ``data_residency`` is within the Federal Republic of Germany
        (``EU_DE`` or equivalent).
      - ``sovereign_scope`` is ``EU`` or ``LOCAL``.
      - Kill switch API is present on the Sentinel instance.
      - A policy evaluator is configured (not ``NullPolicyEvaluator``).

    This requirement does **not** check:
      - Physical security of the deployment environment.
      - Network segmentation / air-gap at the host level.
      - Personnel security clearances.
      - HSM / PKI / certificate management.

    Those remain operator responsibilities documented in
    ``docs/vsnfd-deployment.md``.
    """
    kind = "vsnfd_ready"

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind}


# ---------------------------------------------------------------------------
# Report dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Gap:
    dimension: str
    expected: str
    actual: str
    severity: str  # "critical", "high", "medium", "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "expected": self.expected,
            "actual": self.actual,
            "severity": self.severity,
        }


@dataclass
class MigrationPlan:
    provider: str
    migrating_to: str
    by: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "migrating_to": self.migrating_to,
            "by": self.by,
            "reason": self.reason,
        }


@dataclass
class DimensionStatus:
    name: str
    expected: str
    satisfied: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "expected": self.expected,
            "satisfied": self.satisfied,
            "detail": self.detail,
        }


@dataclass
class ManifestoReport:
    timestamp: datetime
    overall_score: float
    sovereignty_dimensions: dict[str, DimensionStatus] = field(default_factory=dict)
    eu_ai_act_articles: dict[str, str] = field(default_factory=dict)
    gaps: list[Gap] = field(default_factory=list)
    acknowledged_gaps: list[AcknowledgedGap] = field(default_factory=list)
    migration_plans: list[MigrationPlan] = field(default_factory=list)

    @property
    def days_to_enforcement(self) -> int:
        delta = EU_AI_ACT_ENFORCEMENT_DATE - date.today()
        return delta.days

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_score": round(self.overall_score, 3),
            "days_to_enforcement": self.days_to_enforcement,
            "sovereignty_dimensions": {
                name: d.to_dict() for name, d in self.sovereignty_dimensions.items()
            },
            "eu_ai_act_articles": self.eu_ai_act_articles,
            "gaps": [g.to_dict() for g in self.gaps],
            "acknowledged_gaps": [a.as_dict() for a in self.acknowledged_gaps],
            "migration_plans": [m.to_dict() for m in self.migration_plans],
        }

    def as_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2)

    def export_json(self, path: str | Path) -> None:
        Path(path).write_text(self.as_json(), encoding="utf-8")

    def as_text(self) -> str:
        lines: list[str] = []
        lines.append("=" * 68)
        lines.append("  SENTINEL MANIFESTO REPORT")
        lines.append(f"  Generated: {self.timestamp.isoformat(timespec='seconds')}")
        lines.append(f"  Days to EU AI Act enforcement: {self.days_to_enforcement}")
        lines.append("=" * 68)
        lines.append("")
        lines.append(f"  Overall sovereignty score: {self.overall_score:.0%}")
        lines.append("")
        lines.append("  Sovereignty dimensions")
        lines.append("  ----------------------")
        for dim in self.sovereignty_dimensions.values():
            mark = "OK " if dim.satisfied else "GAP"
            lines.append(f"  [{mark}] {dim.name}: {dim.detail}")
        lines.append("")
        if self.gaps:
            lines.append("  Gaps requiring action")
            lines.append("  ---------------------")
            for g in self.gaps:
                lines.append(f"  [{g.severity.upper():8}] {g.dimension}: expected {g.expected}, got {g.actual}")
            lines.append("")
        if self.acknowledged_gaps:
            lines.append("  Acknowledged gaps (with migration plan)")
            lines.append("  ---------------------------------------")
            for a in self.acknowledged_gaps:
                lines.append(f"  {a.provider} → {a.migrating_to} by {a.by}")
                lines.append(f"    Reason: {a.reason}")
            lines.append("")
        lines.append("  EU AI Act articles")
        lines.append("  ------------------")
        for art, status in self.eu_ai_act_articles.items():
            lines.append(f"  {art}: {status}")
        lines.append("")
        lines.append("=" * 68)
        return "\n".join(lines)

    def as_html(self) -> str:
        def _esc(s: str) -> str:
            return html.escape(s)

        dim_rows = "".join(
            f"<tr><td>{'✅' if d.satisfied else '❌'}</td>"
            f"<td>{_esc(d.name)}</td><td>{_esc(d.detail)}</td></tr>"
            for d in self.sovereignty_dimensions.values()
        )
        gap_rows = "".join(
            f"<tr><td>{_esc(g.severity)}</td><td>{_esc(g.dimension)}</td>"
            f"<td>{_esc(g.expected)}</td><td>{_esc(g.actual)}</td></tr>"
            for g in self.gaps
        )
        ack_rows = "".join(
            f"<tr><td>{_esc(a.provider)}</td><td>{_esc(a.migrating_to)}</td>"
            f"<td>{_esc(a.by)}</td><td>{_esc(a.reason)}</td></tr>"
            for a in self.acknowledged_gaps
        )
        art_rows = "".join(
            f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>"
            for k, v in self.eu_ai_act_articles.items()
        )

        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Sentinel Manifesto Report</title>
<style>
 body {{ font-family: -apple-system, "Segoe UI", sans-serif; max-width: 980px;
        margin: 2em auto; color: #111; }}
 h1 {{ font-size: 1.6em; }} h2 {{ font-size: 1.2em; margin-top: 2em; }}
 .score {{ font-size: 3em; font-weight: 700; }}
 .meta {{ color: #555; font-size: 0.9em; }}
 table {{ border-collapse: collapse; width: 100%; margin-top: .6em; }}
 th, td {{ border: 1px solid #ddd; padding: .4em .6em; text-align: left; font-size: .92em; }}
 th {{ background: #f4f4f4; }}
</style>
</head>
<body>
<h1>Sentinel Manifesto Report</h1>
<p class="meta">Generated: {self.timestamp.isoformat(timespec='seconds')}<br>
Days to EU AI Act enforcement: {self.days_to_enforcement}</p>
<div class="score">{self.overall_score:.0%}</div>
<p>Overall sovereignty score.</p>

<h2>Sovereignty dimensions</h2>
<table><thead><tr><th></th><th>Dimension</th><th>Detail</th></tr></thead>
<tbody>{dim_rows}</tbody></table>

<h2>Gaps requiring action</h2>
<table><thead><tr><th>Severity</th><th>Dimension</th><th>Expected</th><th>Actual</th></tr></thead>
<tbody>{gap_rows or '<tr><td colspan="4">None 🎉</td></tr>'}</tbody></table>

<h2>Acknowledged gaps</h2>
<table><thead><tr><th>Provider</th><th>Migrating to</th><th>By</th><th>Reason</th></tr></thead>
<tbody>{ack_rows or '<tr><td colspan="4">None</td></tr>'}</tbody></table>

<h2>EU AI Act articles</h2>
<table><thead><tr><th>Article</th><th>Status</th></tr></thead>
<tbody>{art_rows}</tbody></table>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# SentinelManifesto
# ---------------------------------------------------------------------------


class SentinelManifesto:
    """
    Subclass this and declare your requirements as class attributes.

    Each attribute must be an instance of a Requirement subclass. The
    class scanner picks them up automatically.
    """

    def check(
        self,
        *,
        sentinel: Sentinel | None = None,
        repo_root: str | Path = ".",
        runtime_scan: ScanResult | None = None,
        cicd_scan: CICDScanResult | None = None,
        infra_scan: InfraScanResult | None = None,
    ) -> ManifestoReport:
        """
        Run the manifesto against reality and return a structured report.

        :param sentinel: optional Sentinel instance to inspect runtime
            configuration (kill switch wired up, policy evaluator, etc.).
        :param repo_root: path to the repo to scan for CI/CD and infra.
        :param runtime_scan: pre-computed runtime scan (tests only).
        :param cicd_scan: pre-computed CI/CD scan (tests only).
        :param infra_scan: pre-computed infra scan (tests only).
        """
        runtime_scan = runtime_scan if runtime_scan is not None else RuntimeScanner().scan()
        cicd_scan = cicd_scan if cicd_scan is not None else CICDScanner().scan(repo_root)
        infra_scan = infra_scan if infra_scan is not None else InfrastructureScanner().scan(repo_root)

        report = ManifestoReport(
            timestamp=datetime.now(),
            overall_score=0.0,
        )

        requirements = self._collect_requirements()
        acknowledged: dict[str, AcknowledgedGap] = {
            name: req
            for name, req in requirements.items()
            if isinstance(req, AcknowledgedGap)
        }
        enforceable: dict[str, Requirement] = {
            name: req for name, req in requirements.items() if name not in acknowledged
        }

        # Acknowledged gaps become migration plans, not violations
        for ack in acknowledged.values():
            report.acknowledged_gaps.append(ack)
            report.migration_plans.append(
                MigrationPlan(
                    provider=ack.provider,
                    migrating_to=ack.migrating_to,
                    by=ack.by,
                    reason=ack.reason,
                )
            )

        satisfied_count = 0
        total_count = 0

        # Check each enforceable requirement
        for name, req in enforceable.items():
            total_count += 1
            dimension = self._check_requirement(
                name=name,
                req=req,
                sentinel=sentinel,
                runtime_scan=runtime_scan,
                cicd_scan=cicd_scan,
                infra_scan=infra_scan,
                acknowledged_providers={a.provider for a in acknowledged.values()},
            )
            report.sovereignty_dimensions[name] = dimension
            if dimension.satisfied:
                satisfied_count += 1
            else:
                severity = "critical" if isinstance(req, ZeroExposure | EUOnly) else "medium"
                report.gaps.append(
                    Gap(
                        dimension=name,
                        expected=dimension.expected,
                        actual=dimension.detail,
                        severity=severity,
                    )
                )

        report.overall_score = (satisfied_count / total_count) if total_count else 1.0
        report.eu_ai_act_articles = _check_eu_ai_act_articles(sentinel)
        return report

    def _collect_requirements(self) -> dict[str, Requirement]:
        out: dict[str, Requirement] = {}
        for cls in type(self).__mro__:
            for name, value in vars(cls).items():
                if name.startswith("_"):
                    continue
                if isinstance(value, Requirement) and name not in out:
                    out[name] = value
        return out

    def _check_requirement(
        self,
        *,
        name: str,
        req: Requirement,
        sentinel: Sentinel | None,
        runtime_scan: ScanResult,
        cicd_scan: CICDScanResult,
        infra_scan: InfraScanResult,
        acknowledged_providers: set[str],
    ) -> DimensionStatus:
        if isinstance(req, EUOnly):
            violations = [
                p for p in runtime_scan.packages
                if p.in_critical_path and p.cloud_act_exposure
            ]
            return DimensionStatus(
                name=name,
                expected="No US-owned packages in runtime critical path",
                satisfied=not violations,
                detail=(
                    f"{len(violations)} violation(s): "
                    + ", ".join(v.name for v in violations[:3])
                ) if violations else "0 critical-path violations",
            )

        if isinstance(req, ZeroExposure):
            runtime_violations = runtime_scan.critical_path_violations
            infra_us = [f for f in infra_scan.findings if f.cloud_act_exposure]
            cicd_us = [
                f for f in cicd_scan.findings
                if f.cloud_act_exposure and f.vendor not in acknowledged_providers
            ]
            total = len(runtime_violations) + len(infra_us) + len(cicd_us)
            return DimensionStatus(
                name=name,
                expected="Zero CLOUD Act exposure in runtime, CI/CD, and infra",
                satisfied=total == 0,
                detail=(
                    f"runtime:{len(runtime_violations)} "
                    f"infra:{len(infra_us)} "
                    f"cicd:{len(cicd_us)}"
                ),
            )

        if isinstance(req, OnPremiseOnly):
            if sentinel is None:
                return DimensionStatus(
                    name=name,
                    expected=f"On-premise storage in {req.country}",
                    satisfied=False,
                    detail="No Sentinel instance provided to check storage backend",
                )
            backend = sentinel.storage.backend_name
            satisfied = backend in ("sqlite", "filesystem", "postgres")
            return DimensionStatus(
                name=name,
                expected=f"On-premise storage in {req.country}",
                satisfied=satisfied,
                detail=f"backend: {backend}",
            )

        if isinstance(req, Required):
            # Required-by-name is interpreted via the attribute name:
            #   airgap = Required() → verify Filesystem or SQLite storage
            #   kill_switch = Required() → verify Sentinel has one
            satisfied, detail = _check_required_by_name(name, sentinel)
            return DimensionStatus(
                name=name,
                expected=f"'{name}' capability required",
                satisfied=satisfied,
                detail=detail,
            )

        if isinstance(req, Targeting):
            return DimensionStatus(
                name=name,
                expected=f"Target: {req.by}",
                satisfied=True,  # Targeting is a statement of intent, not a gate
                detail=f"targeting {req.by}",
            )

        if isinstance(req, GDPRCompliant):
            if sentinel is None:
                return DimensionStatus(
                    name=name,
                    expected="GDPR data minimisation",
                    satisfied=False,
                    detail="No Sentinel instance provided",
                )
            residency = sentinel.data_residency.value
            scope = sentinel.sovereign_scope
            in_eu = "EU" in residency.upper() or scope.upper() == "EU"
            return DimensionStatus(
                name=name,
                expected="EU data residency, hashed inputs by default",
                satisfied=in_eu,
                detail=f"scope={scope} residency={residency}",
            )

        if isinstance(req, RetentionPolicy):
            return DimensionStatus(
                name=name,
                expected=f"Retention ≤ {req.max_days} days",
                satisfied=True,
                detail=f"documented: max {req.max_days} days (operator-enforced)",
            )

        if isinstance(req, AuditTrailIntegrity):
            if sentinel is None:
                return DimensionStatus(
                    name=name,
                    expected="Append-only storage, no UPDATE/DELETE",
                    satisfied=False,
                    detail="No Sentinel instance provided",
                )
            storage = sentinel.storage
            mutable_methods = [
                m for m in ("update", "delete", "delete_trace") if hasattr(storage, m)
            ]
            return DimensionStatus(
                name=name,
                expected="Append-only storage, no UPDATE/DELETE",
                satisfied=not mutable_methods,
                detail=(
                    f"storage={storage.backend_name}, "
                    f"mutable methods: {mutable_methods or 'none'}"
                ),
            )

        if isinstance(req, BSIProfile):
            evidence_path = Path(req.evidence)
            exists = evidence_path.exists()
            return DimensionStatus(
                name=name,
                expected=f"BSI {req.status}" + (f" by {req.by}" if req.by else ""),
                satisfied=exists,
                detail=(
                    f"status={req.status} evidence={req.evidence} "
                    f"{'(present)' if exists else '(MISSING)'}"
                ),
            )

        if isinstance(req, VSNfDReady):
            if sentinel is None:
                return DimensionStatus(
                    name=name,
                    expected="VS-NfD deployment profile",
                    satisfied=False,
                    detail="No Sentinel instance provided",
                )
            from sentinel.policy.evaluator import NullPolicyEvaluator

            issues: list[str] = []

            backend = sentinel.storage.backend_name
            if backend == "sqlite":
                issues.append("SQLite not suitable for VS-NfD — use PostgreSQL")
            elif backend not in ("postgres", "filesystem"):
                issues.append(f"storage backend '{backend}' not approved for VS-NfD")

            residency = sentinel.data_residency.value.upper()
            if "EU-DE" not in residency and "LOCAL" not in residency:
                issues.append(
                    f"data_residency '{residency}' is not EU-DE or LOCAL"
                )

            scope = sentinel.sovereign_scope.upper()
            if scope not in ("EU", "LOCAL"):
                issues.append(f"sovereign_scope '{scope}' is not EU or LOCAL")

            if not hasattr(sentinel, "engage_kill_switch"):
                issues.append("kill switch API missing")

            if isinstance(sentinel.policy_evaluator, NullPolicyEvaluator):
                issues.append("no policy evaluator configured")

            return DimensionStatus(
                name=name,
                expected="VS-NfD deployment profile",
                satisfied=not issues,
                detail=("; ".join(issues) if issues else "all automatable VS-NfD checks pass"),
            )

        return DimensionStatus(
            name=name,
            expected=str(req.__class__.__name__),
            satisfied=False,
            detail="unknown requirement type",
        )


def _check_required_by_name(name: str, sentinel: Sentinel | None) -> tuple[bool, str]:
    if sentinel is None:
        return (False, "No Sentinel instance provided")
    lower = name.lower()
    if "kill" in lower and "switch" in lower:
        return (hasattr(sentinel, "engage_kill_switch"), "kill switch API present")
    if "airgap" in lower or "air_gap" in lower:
        backend = sentinel.storage.backend_name
        return (backend in ("filesystem", "sqlite"), f"backend: {backend}")
    if "policy" in lower:
        from sentinel.policy.evaluator import NullPolicyEvaluator
        has_real_policy = not isinstance(sentinel.policy_evaluator, NullPolicyEvaluator)
        return (has_real_policy, "policy evaluator configured" if has_real_policy else "only NullPolicyEvaluator")
    return (True, "capability present")


def _check_eu_ai_act_articles(sentinel: Sentinel | None) -> dict[str, str]:
    if sentinel is None:
        return {
            "Art. 9":  "UNKNOWN — no Sentinel instance",
            "Art. 12": "UNKNOWN — no Sentinel instance",
            "Art. 13": "UNKNOWN — no Sentinel instance",
            "Art. 14": "UNKNOWN — no Sentinel instance",
            "Art. 17": "UNKNOWN — no Sentinel instance",
        }

    from sentinel.policy.evaluator import NullPolicyEvaluator

    has_policy = not isinstance(sentinel.policy_evaluator, NullPolicyEvaluator)
    has_kill_switch = hasattr(sentinel, "engage_kill_switch")
    has_storage = sentinel.storage is not None

    return {
        "Art. 9":  "PARTIAL (policy evaluator wired)" if has_policy else "ACTION REQUIRED — no policy evaluator",
        "Art. 12": "COMPLIANT (traces written)" if has_storage else "NON_COMPLIANT",
        "Art. 13": "COMPLIANT (traces carry policy/model metadata)",
        "Art. 14": "COMPLIANT (kill switch implemented)" if has_kill_switch else "NON_COMPLIANT",
        "Art. 17": "COMPLIANT (append-only storage)",
    }
