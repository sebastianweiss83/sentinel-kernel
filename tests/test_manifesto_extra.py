"""
tests/test_manifesto_extra.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Additional coverage for sentinel.manifesto.base — exercises
serialisation paths, text rendering, and the branches in
_check_requirement / _check_required_by_name / _check_eu_ai_act_articles
that test_manifesto.py does not reach.
"""

from __future__ import annotations

from sentinel import Sentinel
from sentinel.manifesto import (
    AcknowledgedGap,
    EUOnly,
    OnPremiseOnly,
    Required,
    SentinelManifesto,
    Targeting,
    ZeroExposure,
)
from sentinel.manifesto.base import (
    DimensionStatus,
    Gap,
    ManifestoReport,
    MigrationPlan,
    Requirement,
    _check_eu_ai_act_articles,
    _check_required_by_name,
)
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.scanner import CICDScanResult, InfraScanResult, RuntimeScanner
from sentinel.storage import SQLiteStorage

# ---------------------------------------------------------------------------
# Requirement.as_dict — serialisation paths
# ---------------------------------------------------------------------------


def test_requirement_base_as_dict() -> None:
    req = Requirement()
    assert req.as_dict() == {"kind": "requirement", "detail": "Requirement"}


def test_eu_only_as_dict() -> None:
    assert EUOnly().as_dict() == {"kind": "eu_only"}


def test_on_premise_only_as_dict() -> None:
    d = OnPremiseOnly(country="DE").as_dict()
    assert d == {"kind": "on_premise_only", "country": "DE"}


def test_required_as_dict() -> None:
    assert Required().as_dict() == {"kind": "required"}


def test_zero_exposure_as_dict() -> None:
    assert ZeroExposure().as_dict() == {"kind": "zero_exposure"}


def test_targeting_as_dict() -> None:
    d = Targeting(by="2026-12-31").as_dict()
    assert d == {"kind": "targeting", "by": "2026-12-31"}


def test_acknowledged_gap_as_dict() -> None:
    gap = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Forgejo",
        by="2027-Q2",
        reason="No EU-sovereign alternative with comparable UX",
    )
    d = gap.as_dict()
    assert d == {
        "kind": "acknowledged_gap",
        "provider": "GitHub Actions",
        "migrating_to": "Forgejo",
        "by": "2027-Q2",
        "reason": "No EU-sovereign alternative with comparable UX",
    }


# ---------------------------------------------------------------------------
# Gap / MigrationPlan / DimensionStatus serialisation
# ---------------------------------------------------------------------------


def test_gap_to_dict() -> None:
    g = Gap(
        dimension="jurisdiction",
        expected="No US packages",
        actual="1 violation: boto3",
        severity="critical",
    )
    assert g.to_dict() == {
        "dimension": "jurisdiction",
        "expected": "No US packages",
        "actual": "1 violation: boto3",
        "severity": "critical",
    }


def test_migration_plan_to_dict() -> None:
    m = MigrationPlan(
        provider="GitHub Actions",
        migrating_to="Forgejo",
        by="2027-Q2",
        reason="interim",
    )
    assert m.to_dict() == {
        "provider": "GitHub Actions",
        "migrating_to": "Forgejo",
        "by": "2027-Q2",
        "reason": "interim",
    }


def test_dimension_status_to_dict() -> None:
    d = DimensionStatus(
        name="jurisdiction",
        expected="EU only",
        satisfied=True,
        detail="0 violations",
    )
    assert d.to_dict() == {
        "name": "jurisdiction",
        "expected": "EU only",
        "satisfied": True,
        "detail": "0 violations",
    }


# ---------------------------------------------------------------------------
# ManifestoReport.as_text
# ---------------------------------------------------------------------------


def _sentinel(*, with_policy: bool = True) -> Sentinel:
    ev = None
    if with_policy:
        ev = SimpleRuleEvaluator({"p.py": lambda _i: (True, None)})
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        policy_evaluator=ev,
        project="manifesto-extra",
    )


def _clean_runtime():
    return RuntimeScanner(
        installed_packages=[
            ("sentinel-kernel", "1.0.0"),
            ("numpy", "1.26"),
        ]
    ).scan()


def _dirty_runtime():
    return RuntimeScanner(
        installed_packages=[
            ("boto3", "1.34"),
            ("sentinel-kernel", "1.0.0"),
        ]
    ).scan()


def test_as_text_renders_all_sections_with_gaps_and_acknowledged() -> None:
    class M(SentinelManifesto):
        jurisdiction = EUOnly()              # will VIOLATE on dirty runtime
        ci_cd = AcknowledgedGap(
            provider="GitHub Actions",
            migrating_to="Forgejo",
            by="2027-Q2",
            reason="interim",
        )

    report = M().check(
        sentinel=_sentinel(),
        runtime_scan=_dirty_runtime(),
        cicd_scan=CICDScanResult(),
        infra_scan=InfraScanResult(),
    )
    text = report.as_text()
    assert "SENTINEL MANIFESTO REPORT" in text
    assert "Overall sovereignty score" in text
    assert "Sovereignty dimensions" in text
    assert "Gaps requiring action" in text
    assert "Acknowledged gaps" in text
    assert "GitHub Actions" in text
    assert "Forgejo" in text
    assert "EU AI Act articles" in text
    # The dirty runtime produced a critical gap with boto3
    assert "boto3" in text
    assert "CRITICAL" in text


def test_as_text_without_gaps_skips_gap_section() -> None:
    class M(SentinelManifesto):
        jurisdiction = EUOnly()

    report = M().check(
        sentinel=_sentinel(),
        runtime_scan=_clean_runtime(),
        cicd_scan=CICDScanResult(),
        infra_scan=InfraScanResult(),
    )
    text = report.as_text()
    assert "Gaps requiring action" not in text
    assert "Acknowledged gaps" not in text
    assert "EU AI Act articles" in text


# ---------------------------------------------------------------------------
# _check_requirement branches
# ---------------------------------------------------------------------------


def test_on_premise_only_without_sentinel_is_unsatisfied() -> None:
    class M(SentinelManifesto):
        storage = OnPremiseOnly(country="DE")

    report = M().check(
        sentinel=None,
        runtime_scan=_clean_runtime(),
        cicd_scan=CICDScanResult(),
        infra_scan=InfraScanResult(),
    )
    dim = report.sovereignty_dimensions["storage"]
    assert dim.satisfied is False
    assert "No Sentinel instance" in dim.detail


def test_targeting_counts_as_satisfied_intent() -> None:
    class M(SentinelManifesto):
        bsi = Targeting(by="2026-Q4")

    report = M().check(
        sentinel=_sentinel(),
        runtime_scan=_clean_runtime(),
        cicd_scan=CICDScanResult(),
        infra_scan=InfraScanResult(),
    )
    dim = report.sovereignty_dimensions["bsi"]
    assert dim.satisfied is True
    assert "targeting 2026-Q4" in dim.detail


def test_unknown_requirement_subclass_falls_through() -> None:
    class CustomReq(Requirement):
        kind = "custom"

    class M(SentinelManifesto):
        custom = CustomReq()

    report = M().check(
        sentinel=_sentinel(),
        runtime_scan=_clean_runtime(),
        cicd_scan=CICDScanResult(),
        infra_scan=InfraScanResult(),
    )
    dim = report.sovereignty_dimensions["custom"]
    assert dim.satisfied is False
    assert dim.detail == "unknown requirement type"
    assert dim.expected == "CustomReq"


# ---------------------------------------------------------------------------
# _check_required_by_name branches
# ---------------------------------------------------------------------------


def test_required_by_name_without_sentinel() -> None:
    satisfied, detail = _check_required_by_name("kill_switch", sentinel=None)
    assert satisfied is False
    assert "No Sentinel instance" in detail


def test_required_by_name_kill_switch_present() -> None:
    satisfied, detail = _check_required_by_name("kill_switch", sentinel=_sentinel())
    assert satisfied is True
    assert "kill switch" in detail.lower()


def test_required_by_name_airgap_with_sqlite_backend() -> None:
    satisfied, detail = _check_required_by_name("airgap", sentinel=_sentinel())
    assert satisfied is True
    assert "backend:" in detail


def test_required_by_name_policy_true_when_configured() -> None:
    satisfied, detail = _check_required_by_name(
        "policy", sentinel=_sentinel(with_policy=True)
    )
    assert satisfied is True
    assert "policy evaluator configured" in detail


def test_required_by_name_policy_false_when_null_evaluator() -> None:
    satisfied, detail = _check_required_by_name(
        "policy", sentinel=_sentinel(with_policy=False)
    )
    assert satisfied is False
    assert "NullPolicyEvaluator" in detail


def test_required_by_name_generic_capability_default_true() -> None:
    satisfied, detail = _check_required_by_name("some_other_thing", sentinel=_sentinel())
    assert satisfied is True
    assert detail == "capability present"


# ---------------------------------------------------------------------------
# _check_eu_ai_act_articles without Sentinel
# ---------------------------------------------------------------------------


def test_eu_ai_act_articles_unknown_when_no_sentinel() -> None:
    out = _check_eu_ai_act_articles(sentinel=None)
    assert set(out.keys()) == {"Art. 9", "Art. 12", "Art. 13", "Art. 14", "Art. 17"}
    for value in out.values():
        assert value.startswith("UNKNOWN")


# ---------------------------------------------------------------------------
# ManifestoReport helpers
# ---------------------------------------------------------------------------


def test_report_as_dict_round_trips_core_fields() -> None:
    from datetime import datetime

    r = ManifestoReport(timestamp=datetime(2026, 4, 11, 12, 0, 0), overall_score=0.75)
    r.sovereignty_dimensions["jurisdiction"] = DimensionStatus(
        name="jurisdiction",
        expected="EU only",
        satisfied=True,
        detail="0 violations",
    )
    r.gaps.append(
        Gap(
            dimension="x",
            expected="y",
            actual="z",
            severity="medium",
        )
    )
    r.migration_plans.append(
        MigrationPlan(
            provider="GitHub Actions",
            migrating_to="Forgejo",
            by="2027-Q2",
            reason="interim",
        )
    )
    r.eu_ai_act_articles = {"Art. 12": "COMPLIANT"}

    d = r.as_dict()
    assert d["overall_score"] == 0.75
    assert d["sovereignty_dimensions"]["jurisdiction"]["satisfied"] is True
    assert d["gaps"][0]["severity"] == "medium"
    assert d["migration_plans"][0]["provider"] == "GitHub Actions"
    assert d["eu_ai_act_articles"]["Art. 12"] == "COMPLIANT"
    assert "days_to_enforcement" in d


def test_as_json_is_valid_json() -> None:
    import json
    from datetime import datetime

    r = ManifestoReport(timestamp=datetime(2026, 4, 11), overall_score=1.0)
    parsed = json.loads(r.as_json())
    assert parsed["overall_score"] == 1.0
