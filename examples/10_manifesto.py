"""
10 — Manifesto-as-code — three industry scenarios.

Declares three realistic sovereignty manifestos: defence, healthcare,
enterprise. Runs each against the same Sentinel instance to show how
different industries express their non-negotiables in code.

Run:
    python examples/10_manifesto.py
"""

from __future__ import annotations

from sentinel import DataResidency, Sentinel
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
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


class DefencePolicy(SentinelManifesto):
    """VS-NfD-track defence contractor — strictest posture.

    Air-gap mandatory, BSI pursued, no CLOUD Act exposure anywhere,
    and audit-trail integrity enforced at the storage layer.
    """

    jurisdiction = EUOnly()
    cloud_act    = ZeroExposure()
    kill_switch  = Required()
    airgap       = Required()
    storage      = OnPremiseOnly(country="DE")
    audit        = AuditTrailIntegrity()
    bsi          = BSIProfile(status="pursuing", by="2026-Q4", evidence="docs/bsi-profile.md")
    retention    = RetentionPolicy(max_days=365 * 10)  # 10 years


class HealthcarePolicy(SentinelManifesto):
    """Hospital AI triage — GDPR-first, BSI targeted.

    Retention is constrained by national healthcare law; consult
    your DPO before changing the default.
    """

    jurisdiction = EUOnly()
    kill_switch  = Required()
    gdpr         = GDPRCompliant()
    storage      = OnPremiseOnly(country="EU")
    retention    = RetentionPolicy(max_days=365 * 10)
    bsi          = Targeting(by="2027-Q2")

    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q1",
        reason="Trust boundary is the data zone, not CI. Low priority.",
    )


class EnterprisePolicy(SentinelManifesto):
    """Generic EU enterprise — pragmatic posture.

    Documents acknowledged gaps openly rather than pretending they
    do not exist. Migration plans are dated.
    """

    jurisdiction = EUOnly()
    kill_switch  = Required()
    gdpr         = GDPRCompliant()
    storage      = OnPremiseOnly(country="EU")
    retention    = RetentionPolicy(max_days=365 * 7)

    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No EU-sovereign CI with comparable UX today",
    )
    package_registry = AcknowledgedGap(
        provider="pypi.org",
        migrating_to="self-hosted devpi EU mirror",
        by="2027-Q4",
        reason="Mirror build in progress",
    )


def _make_sentinel() -> Sentinel:
    def policy(inputs: dict[str, object]) -> tuple[bool, str | None]:
        return True, None

    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="manifesto-demo",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator({"p.py": policy}),
    )


def main() -> None:
    sentinel = _make_sentinel()

    for name, policy_cls in [
        ("DEFENCE   (VS-NfD)",   DefencePolicy),
        ("HEALTHCARE (GDPR)",    HealthcarePolicy),
        ("ENTERPRISE (pragmatic)", EnterprisePolicy),
    ]:
        print("=" * 64)
        print(f"  {name}")
        print("=" * 64)
        report = policy_cls().check(sentinel=sentinel)
        print(f"  Overall score      : {report.overall_score:.0%}")
        print(f"  Acknowledged gaps  : {len(report.acknowledged_gaps)}")
        print(f"  Unresolved gaps    : {len(report.gaps)}")
        print(f"  Days to enforcement: {report.days_to_enforcement}")
        print()
        print("  Dimensions:")
        for dim_name, dim in report.sovereignty_dimensions.items():
            mark = "OK " if dim.satisfied else "GAP"
            print(f"    [{mark}] {dim_name}: {dim.detail}")
        if report.acknowledged_gaps:
            print()
            print("  Acknowledged gaps (honest reporting, not violations):")
            for ack in report.acknowledged_gaps:
                print(f"    - {ack.provider} → {ack.migrating_to} by {ack.by}")
        print()


if __name__ == "__main__":
    main()
