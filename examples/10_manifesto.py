"""
10 — Manifesto-as-code.

Declare sovereignty requirements as a Python class. Run against
reality. Get a structured report with COMPLIANT / VIOLATION /
ACKNOWLEDGED / TARGETING statuses.

Run:
    python examples/10_manifesto.py
"""

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
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


class OurPolicy(SentinelManifesto):
    """Example manifesto for a regulated organisation."""

    # Hard requirements
    jurisdiction = EUOnly()
    cloud_act = ZeroExposure()
    kill_switch = Required()
    storage = OnPremiseOnly(country="DE")

    # Future target (non-gating)
    bsi = Targeting(by="2026-12-31")

    # Honest acknowledged gap with a migration plan
    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No EU-sovereign CI alternative with comparable UX today",
    )


def main() -> None:
    def policy(inputs: dict) -> tuple[bool, str | None]:
        return True, None

    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="manifesto-demo",
        policy_evaluator=SimpleRuleEvaluator({"p.py": policy}),
    )

    report = OurPolicy().check(sentinel=sentinel)
    print(report.as_text())

    print(f"\nOverall score      : {report.overall_score:.0%}")
    print(f"Days to enforcement: {report.days_to_enforcement}")
    print(f"Acknowledged gaps  : {len(report.acknowledged_gaps)}")
    print(f"Unresolved gaps    : {len(report.gaps)}")


if __name__ == "__main__":
    main()
