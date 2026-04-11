#!/usr/bin/env python3
"""
Thesis 4: Sentinel passes its own sovereignty manifesto.

If we build tools to verify sovereignty, we must be sovereign ourselves.
This script runs Sentinel's own manifesto check and fails CI if any
HARD requirement (not AcknowledgedGap) shows a violation.

Acknowledged gaps (GitHub Actions, PyPI) are printed but do not fail CI.
This is honest: we know our gaps, we have migration plans.

Exit 0: all hard requirements pass (gaps acknowledged)
Exit 1: hard requirement violation found
"""

from __future__ import annotations

import sys

from sentinel import Sentinel
from sentinel.manifesto import (
    AcknowledgedGap,
    EUOnly,
    OnPremiseOnly,
    Required,
    SentinelManifesto,
    ZeroExposure,
)


class SentinelSelfManifesto(SentinelManifesto):
    """Sentinel's own sovereignty policy — dogfooding Thesis 4."""

    jurisdiction = EUOnly()
    kill_switch = Required()
    airgap = Required()  # interpreted via _check_required_by_name
    cloud_act = ZeroExposure()
    storage = OnPremiseOnly(country="EU")

    ci_cd = AcknowledgedGap(
        provider="GitHub (Microsoft)",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No production-ready EU-sovereign CI alternative today",
    )
    package_registry = AcknowledgedGap(
        provider="PyPI (US-hosted infrastructure)",
        migrating_to="EU private mirror (Devpi)",
        by="2027-Q4",
        reason="Package content is not US-controlled; mirror planned",
    )


def main() -> int:
    sentinel = Sentinel(project="sentinel-self-check")

    report = SentinelSelfManifesto().check(sentinel=sentinel, repo_root=".")

    print("━" * 64)
    print("  Sentinel self-manifesto check — Thesis 4 dogfood")
    print("━" * 64)
    print()

    # Hard requirements
    any_failures = False
    for name, dim in report.sovereignty_dimensions.items():
        marker = "✓ PASS" if dim.satisfied else "✗ FAIL"
        print(f"  {marker}  {name:<20} — {dim.detail}")
        if not dim.satisfied:
            any_failures = True

    print()
    if report.acknowledged_gaps:
        print("  ACKNOWLEDGED GAPS (honest, not failures):")
        for gap in report.acknowledged_gaps:
            print(f"    - {gap.provider}")
            print(f"        migrating to: {gap.migrating_to} by {gap.by}")
            print(f"        reason: {gap.reason}")
        print()

    print(f"  Overall score: {report.overall_score:.0%}")
    print(f"  EU AI Act articles checked: {len(report.eu_ai_act_articles)}")
    print()

    if any_failures:
        print("SELF-MANIFESTO CHECK FAILED")
        print("A hard requirement violation means Sentinel cannot honestly claim")
        print("to verify sovereignty for others. Fix the violation and retry.")
        return 1

    print("✓ Sentinel passes its own sovereignty manifesto.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
