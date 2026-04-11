"""
13 — Full pipeline: the complete picture.

Brings every core capability together in one script:
  - Sentinel + SQLite storage + SimpleRule policy
  - Kill switch engage / block / disengage
  - Scanner: runtime + CI/CD + infrastructure
  - Manifesto with an acknowledged gap
  - EU AI Act compliance check
  - Self-contained HTML report written to disk

Zero optional extras required. Zero network calls.

Run:
    python examples/13_full_pipeline.py
"""

from __future__ import annotations

import contextlib
import shutil
import tempfile
from pathlib import Path

from sentinel import (
    DataResidency,
    KillSwitchEngaged,
    PolicyDeniedError,
    PolicyResult,
    Sentinel,
)
from sentinel.compliance import EUAIActChecker
from sentinel.dashboard import HTMLReport
from sentinel.manifesto import (
    AcknowledgedGap,
    EUOnly,
    OnPremiseOnly,
    Required,
    SentinelManifesto,
)
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.scanner import RuntimeScanner
from sentinel.storage import SQLiteStorage


class OrganisationPolicy(SentinelManifesto):
    jurisdiction = EUOnly()
    kill_switch = Required()
    storage = OnPremiseOnly(country="DE")
    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No comparable EU-sovereign CI alternative today",
    )


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="sentinel-full-"))
    try:
        def approval_policy(inputs: dict) -> tuple[bool, str | None]:
            request = inputs.get("request", {})
            if request.get("amount", 0) > 10_000:
                return False, "amount_exceeds_cap"
            return True, None

        sentinel = Sentinel(
            storage=SQLiteStorage(str(tmp / "traces.db")),
            project="full-pipeline",
            data_residency=DataResidency.EU_DE,
            sovereign_scope="EU",
            policy_evaluator=SimpleRuleEvaluator({
                "policies/approval.py": approval_policy,
            }),
        )

        @sentinel.trace(policy="policies/approval.py")
        def approve(request: dict) -> dict:
            return {"decision": "approved", "amount": request["amount"]}

        # Normal operation
        approve(request={"amount": 5_000})
        with contextlib.suppress(PolicyDeniedError):
            approve(request={"amount": 50_000})

        # Kill switch
        sentinel.engage_kill_switch("mid-pipeline drill")
        with contextlib.suppress(KillSwitchEngaged):
            approve(request={"amount": 100})
        sentinel.disengage_kill_switch("drill complete")
        approve(request={"amount": 1_500})

        # Scanner
        scan = RuntimeScanner().scan()

        # Manifesto
        manifesto_report = OrganisationPolicy().check(sentinel=sentinel)

        # EU AI Act compliance
        compliance = EUAIActChecker().check(sentinel)

        # Self-contained HTML report
        html_path = tmp / "report.html"
        html = HTMLReport().generate(sentinel, manifesto=OrganisationPolicy())
        html_path.write_text(html, encoding="utf-8")

        # Summary
        all_traces = sentinel.query(limit=100)
        deny_traces = sentinel.query(policy_result=PolicyResult.DENY, limit=100)

        print("=" * 64)
        print("  FULL PIPELINE RESULT")
        print("=" * 64)
        print(f"  Traces written     : {len(all_traces)}")
        print(f"  DENY traces        : {len(deny_traces)}")
        print(f"  Sovereignty score  : {scan.sovereignty_score:.0%}")
        print(f"  Manifesto score    : {manifesto_report.overall_score:.0%}")
        print(f"  EU AI Act overall  : {compliance.overall}")
        print(f"  Automated coverage : {compliance.automated_coverage:.0%}")
        print(f"  Days to enforcement: {compliance.days_to_enforcement}")
        print(f"  HTML report        : {html_path.name} ({html_path.stat().st_size} bytes)")
        print("=" * 64)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
