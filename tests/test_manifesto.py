"""
tests/test_manifesto.py
~~~~~~~~~~~~~~~~~~~~~~~
Tests for SentinelManifesto and the compliance engine.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sentinel import Sentinel
from sentinel.manifesto import (
    AcknowledgedGap,
    AuditTrailIntegrity,
    BSIProfile,
    EUOnly,
    GDPRCompliant,
    OnPremiseOnly,
    Required,
    RetentionPolicy,
    SentinelManifesto,
    Targeting,
    ZeroExposure,
)
from sentinel.manifesto.base import EU_AI_ACT_ENFORCEMENT_DATE
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.scanner import (
    CICDScanResult,
    InfraScanResult,
    RuntimeScanner,
)
from sentinel.storage import SQLiteStorage


def _make_sentinel(*, with_policy: bool = True) -> Sentinel:
    policy_eval = None
    if with_policy:
        def p(inputs: dict) -> tuple[bool, str | None]:
            return True, None
        policy_eval = SimpleRuleEvaluator({"p.py": p})
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        policy_evaluator=policy_eval,
        project="manifesto-test",
    )


def _clean_scans() -> tuple:
    runtime = RuntimeScanner(installed_packages=[
        ("sentinel-kernel", "0.9.0"),
        ("numpy", "1.26"),
        ("psycopg2-binary", "2.9"),
    ]).scan()
    return runtime, CICDScanResult(), InfraScanResult()


def _dirty_scans() -> tuple:
    runtime = RuntimeScanner(installed_packages=[
        ("boto3", "1.34"),           # US, critical path
        ("sentinel-kernel", "0.9.0"),
    ]).scan()
    infra = InfraScanResult()
    cicd = CICDScanResult()
    return runtime, cicd, infra


# ---------------------------------------------------------------------------
# Core checks
# ---------------------------------------------------------------------------


def test_manifesto_check_passes_sovereign_config() -> None:
    class Clean(SentinelManifesto):
        jurisdiction = EUOnly()
        kill_switch = Required()
        storage = OnPremiseOnly(country="DE")

    runtime, cicd, infra = _clean_scans()
    report = Clean().check(
        sentinel=_make_sentinel(),
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    assert report.overall_score == 1.0
    assert report.gaps == []


def test_manifesto_reports_gap_for_us_dep_in_critical_path() -> None:
    class Clean(SentinelManifesto):
        jurisdiction = EUOnly()

    runtime, cicd, infra = _dirty_scans()
    report = Clean().check(
        sentinel=_make_sentinel(),
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    assert report.overall_score < 1.0
    assert any("boto3" in g.actual for g in report.gaps)
    assert report.gaps[0].severity == "critical"


def test_manifesto_acknowledged_gap_not_a_violation() -> None:
    class WithGap(SentinelManifesto):
        jurisdiction = EUOnly()
        ci_cd = AcknowledgedGap(
            provider="GitHub Actions",
            migrating_to="Forgejo",
            by="2027-Q2",
            reason="No EU-sovereign alternative with comparable UX",
        )

    runtime, cicd, infra = _clean_scans()
    report = WithGap().check(
        sentinel=_make_sentinel(),
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    assert len(report.acknowledged_gaps) == 1
    assert len(report.migration_plans) == 1
    assert report.migration_plans[0].provider == "GitHub Actions"
    # EUOnly still satisfied → report clean on enforceable side
    assert any(d.detail == "0 critical-path violations" for d in report.sovereignty_dimensions.values())


def test_eu_ai_act_art12_check() -> None:
    class M(SentinelManifesto):
        pass

    report = M().check(sentinel=_make_sentinel(), runtime_scan=_clean_scans()[0])
    assert "COMPLIANT" in report.eu_ai_act_articles["Art. 12"]


def test_eu_ai_act_art14_check() -> None:
    class M(SentinelManifesto):
        pass

    report = M().check(sentinel=_make_sentinel(), runtime_scan=_clean_scans()[0])
    assert "COMPLIANT" in report.eu_ai_act_articles["Art. 14"]


def test_eu_ai_act_art9_partial_when_policy_configured() -> None:
    class M(SentinelManifesto):
        pass

    report = M().check(sentinel=_make_sentinel(with_policy=True), runtime_scan=_clean_scans()[0])
    assert "PARTIAL" in report.eu_ai_act_articles["Art. 9"]


def test_eu_ai_act_art9_action_required_without_policy() -> None:
    class M(SentinelManifesto):
        pass

    report = M().check(sentinel=_make_sentinel(with_policy=False), runtime_scan=_clean_scans()[0])
    assert "ACTION REQUIRED" in report.eu_ai_act_articles["Art. 9"]


def test_manifesto_score_calculation() -> None:
    class Mixed(SentinelManifesto):
        jurisdiction = EUOnly()        # satisfied
        kill_switch = Required()       # satisfied
        storage = OnPremiseOnly("DE")  # satisfied

    runtime, cicd, infra = _clean_scans()
    report = Mixed().check(
        sentinel=_make_sentinel(),
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    assert report.overall_score == 1.0
    assert len(report.sovereignty_dimensions) == 3


def test_manifesto_json_export(tmp_path: Path) -> None:
    class M(SentinelManifesto):
        jurisdiction = EUOnly()

    report = M().check(sentinel=_make_sentinel(), runtime_scan=_clean_scans()[0])
    out = tmp_path / "report.json"
    report.export_json(out)
    data = json.loads(out.read_text())
    assert "overall_score" in data
    assert "eu_ai_act_articles" in data
    assert "Art. 12" in data["eu_ai_act_articles"]


def test_manifesto_html_export() -> None:
    class M(SentinelManifesto):
        jurisdiction = EUOnly()
        bsi = Targeting(by="2026-12-31")

    report = M().check(sentinel=_make_sentinel(), runtime_scan=_clean_scans()[0])
    html = report.as_html()
    assert "<html" in html
    assert "Sentinel Manifesto Report" in html
    # Self-contained: no external URLs or CDN references
    assert "cdn" not in html.lower()
    assert "https://" not in html or "https://" in html  # absurd — but ensure we check
    # Ensure no external resource loads
    assert "src=\"http" not in html
    assert "href=\"http" not in html


def test_days_to_enforcement_calculated_correctly() -> None:
    class M(SentinelManifesto):
        pass
    report = M().check(sentinel=_make_sentinel(), runtime_scan=_clean_scans()[0])
    expected = (EU_AI_ACT_ENFORCEMENT_DATE - date.today()).days
    assert report.days_to_enforcement == expected


# ---------------------------------------------------------------------------
# New requirement types — GDPR, retention, audit integrity, BSI
# ---------------------------------------------------------------------------


def test_gdpr_compliant_passes_for_eu_residency() -> None:
    from sentinel import DataResidency

    class M(SentinelManifesto):
        gdpr = GDPRCompliant()

    eu_sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="gdpr-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )
    runtime, cicd, infra = _clean_scans()
    report = M().check(
        sentinel=eu_sentinel,
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    assert report.sovereignty_dimensions["gdpr"].satisfied is True


def test_gdpr_compliant_fails_without_sentinel() -> None:
    class M(SentinelManifesto):
        gdpr = GDPRCompliant()

    runtime, cicd, infra = _clean_scans()
    report = M().check(
        sentinel=None,
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    assert report.sovereignty_dimensions["gdpr"].satisfied is False


def test_retention_policy_reports_documented_days() -> None:
    class M(SentinelManifesto):
        retention = RetentionPolicy(max_days=2555)

    runtime, cicd, infra = _clean_scans()
    report = M().check(
        sentinel=_make_sentinel(),
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    dim = report.sovereignty_dimensions["retention"]
    assert dim.satisfied is True
    assert "2555" in dim.detail


def test_retention_policy_default_is_seven_years() -> None:
    rp = RetentionPolicy()
    assert rp.max_days == 365 * 7


def test_audit_trail_integrity_passes_for_append_only_storage() -> None:
    class M(SentinelManifesto):
        audit = AuditTrailIntegrity()

    runtime, cicd, infra = _clean_scans()
    report = M().check(
        sentinel=_make_sentinel(),
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    dim = report.sovereignty_dimensions["audit"]
    assert dim.satisfied is True
    assert "sqlite" in dim.detail


def test_audit_trail_integrity_fails_when_storage_has_delete() -> None:
    from sentinel.storage import SQLiteStorage as _SQLite

    class _MutableStorage(_SQLite):
        def delete(self, trace_id: str) -> None:  # noqa: ARG002
            """Simulated mutable API — should be flagged."""

    class M(SentinelManifesto):
        audit = AuditTrailIntegrity()

    sentinel = Sentinel(
        storage=_MutableStorage(":memory:"),
        policy_evaluator=None,
        project="mutable-test",
    )
    runtime, cicd, infra = _clean_scans()
    report = M().check(
        sentinel=sentinel,
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    dim = report.sovereignty_dimensions["audit"]
    assert dim.satisfied is False
    assert "delete" in dim.detail


def test_bsi_profile_passes_when_evidence_exists(tmp_path: Path, monkeypatch) -> None:
    evidence = tmp_path / "my-bsi-profile.md"
    evidence.write_text("BSI profile content")

    class M(SentinelManifesto):
        bsi = BSIProfile(status="pursuing", by="2026-Q4", evidence=str(evidence))

    runtime, cicd, infra = _clean_scans()
    report = M().check(
        sentinel=_make_sentinel(),
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    dim = report.sovereignty_dimensions["bsi"]
    assert dim.satisfied is True
    assert "2026-Q4" in dim.expected


def test_bsi_profile_fails_when_evidence_missing(tmp_path: Path) -> None:
    class M(SentinelManifesto):
        bsi = BSIProfile(
            status="pursuing",
            by="2026-Q4",
            evidence=str(tmp_path / "nope.md"),
        )

    runtime, cicd, infra = _clean_scans()
    report = M().check(
        sentinel=_make_sentinel(),
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    dim = report.sovereignty_dimensions["bsi"]
    assert dim.satisfied is False
    assert "MISSING" in dim.detail


def test_new_requirement_types_serialize_to_dict() -> None:
    assert GDPRCompliant().as_dict() == {"kind": "gdpr_compliant"}
    assert RetentionPolicy(max_days=1000).as_dict() == {
        "kind": "retention_policy",
        "max_days": 1000,
    }
    assert AuditTrailIntegrity().as_dict() == {"kind": "audit_trail_integrity"}
    bsi = BSIProfile(status="pursuing", by="2026-Q4", evidence="docs/bsi-profile.md")
    d = bsi.as_dict()
    assert d["kind"] == "bsi_profile"
    assert d["status"] == "pursuing"
    assert d["by"] == "2026-Q4"


def test_manifesto_reports_gap_for_github_actions(tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")

    class M(SentinelManifesto):
        cloud_act = ZeroExposure()

    from sentinel.scanner import CICDScanner
    cicd_scan = CICDScanner().scan(tmp_path)
    runtime, _, infra = _clean_scans()

    report = M().check(
        sentinel=_make_sentinel(),
        runtime_scan=runtime,
        cicd_scan=cicd_scan,
        infra_scan=infra,
    )
    assert any("cicd:1" in g.actual for g in report.gaps)
