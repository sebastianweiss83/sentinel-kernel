"""
examples/manifesto_example.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Three organisations, three different sovereignty postures.

Run: python examples/manifesto_example.py
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
from sentinel.storage import FilesystemStorage


# ---------------------------------------------------------------------------
# 1. Defence contractor — maximum sovereignty, no exceptions
# ---------------------------------------------------------------------------


class DefenceContractor(SentinelManifesto):
    jurisdiction = EUOnly()
    cloud_act = ZeroExposure()
    airgap = Required()
    kill_switch = Required()
    storage = OnPremiseOnly(country="DE")
    bsi = Targeting(by="2026-12-31")


# ---------------------------------------------------------------------------
# 2. Hospital — EU jurisdiction, pragmatic about observability
# ---------------------------------------------------------------------------


class Hospital(SentinelManifesto):
    jurisdiction = EUOnly()
    kill_switch = Required()
    storage = OnPremiseOnly(country="DE")
    observability = AcknowledgedGap(
        provider="Grafana Cloud",
        migrating_to="Grafana self-hosted (on-prem)",
        by="2027-Q1",
        reason="Interim observability until on-prem Grafana rolled out",
    )


# ---------------------------------------------------------------------------
# 3. Startup — honest about gaps, working toward v1.0 compliance
# ---------------------------------------------------------------------------


class EarlyStartup(SentinelManifesto):
    kill_switch = Required()
    eu_ai_act_compliance = Targeting(by="2026-08-02")
    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Forgejo self-hosted",
        by="2027-Q2",
        reason="No EU-sovereign CI alternative with GitHub-comparable UX yet",
    )
    package_registry = AcknowledgedGap(
        provider="PyPI",
        migrating_to="devpi mirror",
        by="2026-Q4",
        reason="Mirror will run inside EU-sovereign network perimeter",
    )


def main() -> None:
    def policy(inputs: dict) -> tuple[bool, str | None]:
        return True, None

    sentinel = Sentinel(
        storage=FilesystemStorage("./sentinel-manifesto-demo"),
        policy_evaluator=SimpleRuleEvaluator({"p.py": policy}),
        project="manifesto-demo",
    )

    for org_cls in (DefenceContractor, Hospital, EarlyStartup):
        print("=" * 70)
        print(f"  {org_cls.__name__}")
        print("=" * 70)
        report = org_cls().check(sentinel=sentinel, repo_root=".")
        print(report.as_text())
        print()


if __name__ == "__main__":
    main()
