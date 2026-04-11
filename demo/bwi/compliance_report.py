"""
demo/bwi/compliance_report.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Generate a BWI-specific compliance report.

Runs the full EU AI Act checker, the sovereignty scanner, and the
defence-contractor manifesto against the current repository and
writes a single self-contained HTML report suitable for review.

Run: python demo/bwi/compliance_report.py
Output: bwi_compliance_report.html (in the current directory)
"""

from __future__ import annotations

import sys
from pathlib import Path

from sentinel import DataResidency, Sentinel
from sentinel.dashboard import HTMLReport
from sentinel.manifesto import (
    EUOnly,
    OnPremiseOnly,
    Required,
    SentinelManifesto,
    Targeting,
    ZeroExposure,
)
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


class BWIProfile(SentinelManifesto):
    """Manifesto for a BWI-operated federal AI deployment."""

    jurisdiction = EUOnly()
    cloud_act = ZeroExposure()
    kill_switch = Required()
    airgap = Required()
    storage = OnPremiseOnly(country="DE")
    bsi = Targeting(by="2026-12-31")


def main() -> int:
    def policy(inputs: dict) -> tuple[bool, str | None]:
        return True, None

    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="bwi-compliance",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator({"p.py": policy}),
    )

    html = HTMLReport().generate(sentinel, manifesto=BWIProfile())
    out = Path("bwi_compliance_report.html")
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out.resolve()}")
    print("Open it in a browser for the full report.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
