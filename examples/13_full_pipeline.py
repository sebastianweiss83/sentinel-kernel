"""
13 — Full pipeline: the complete picture.

A realistic document classification and approval workflow that
touches every core Sentinel capability:

  1. Document classifier agent (sensitivity triage)
  2. Approval agent (policy-gated)
  3. Kill switch engage / block / disengage
  4. Runtime + CI/CD sovereignty scan
  5. Manifesto check with an acknowledged gap
  6. EU AI Act Art. 9/12/13/14/17 compliance check
  7. Self-contained HTML report written to disk
  8. Terminal summary with totals and links

Zero optional extras required. Zero network calls. Runs in <2 seconds.

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
    BSIProfile,
    EUOnly,
    OnPremiseOnly,
    Required,
    SentinelManifesto,
)
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.scanner import CICDScanner, RuntimeScanner
from sentinel.storage import SQLiteStorage


class OrganisationPolicy(SentinelManifesto):
    jurisdiction = EUOnly()
    kill_switch  = Required()
    storage      = OnPremiseOnly(country="DE")
    bsi          = BSIProfile(status="pursuing", by="2026-Q4", evidence="docs/bsi-profile.md")
    ci_cd = AcknowledgedGap(
        provider="GitHub Actions",
        migrating_to="Self-hosted Forgejo",
        by="2027-Q2",
        reason="No comparable EU-sovereign CI alternative today",
    )


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="sentinel-full-"))
    try:
        def approval_policy(inputs: dict[str, object]) -> tuple[bool, str | None]:
            request = inputs.get("request", {})
            assert isinstance(request, dict)
            if request.get("classification") == "RESTRICTED":
                return False, "classified_documents_require_manual_review"
            if request.get("amount", 0) > 10_000:
                return False, "amount_exceeds_cap"
            return True, None

        sentinel = Sentinel(
            storage=SQLiteStorage(str(tmp / "traces.db")),
            project="full-pipeline",
            data_residency=DataResidency.EU_DE,
            sovereign_scope="EU",
            policy_evaluator=SimpleRuleEvaluator({"policies/approval.py": approval_policy}),
        )

        @sentinel.trace(agent_name="doc_classifier")
        def classify(document: dict[str, str]) -> dict[str, str]:
            sensitive_terms = ("confidential", "restricted", "internal only")
            body = document.get("body", "").lower()
            return {
                "classification": "RESTRICTED" if any(t in body for t in sensitive_terms) else "PUBLIC",
                "doc_id": document["doc_id"],
            }

        @sentinel.trace(policy="policies/approval.py", agent_name="approval_agent")
        def approve(request: dict[str, object]) -> dict[str, object]:
            return {"decision": "approved", "doc_id": request["doc_id"]}

        docs = [
            {"doc_id": "d1", "body": "Quarterly sales report", "amount": 5_000},
            {"doc_id": "d2", "body": "Confidential merger plan", "amount": 2_000},
            {"doc_id": "d3", "body": "Marketing brochure", "amount": 50_000},
        ]

        # Step 1+2: classify → approve chain
        for doc in docs:
            cls = classify(document=doc)
            with contextlib.suppress(PolicyDeniedError):
                approve(request={
                    "doc_id": doc["doc_id"],
                    "classification": cls["classification"],
                    "amount": doc["amount"],
                })

        # Step 3: kill switch drill
        sentinel.engage_kill_switch("incident response drill")
        with contextlib.suppress(KillSwitchEngaged):
            approve(request={"doc_id": "halted", "amount": 100})
        sentinel.disengage_kill_switch("drill complete")
        with contextlib.suppress(PolicyDeniedError):
            approve(request={"doc_id": "post-drill", "amount": 1_500})

        # Step 4: scanners
        runtime = RuntimeScanner().scan()
        cicd = CICDScanner().scan(".")

        # Step 5: manifesto
        manifesto_report = OrganisationPolicy().check(sentinel=sentinel)

        # Step 6: EU AI Act
        compliance = EUAIActChecker().check(sentinel)

        # Step 7: HTML report
        html_path = tmp / "report.html"
        html = HTMLReport().generate(sentinel, manifesto=OrganisationPolicy())
        html_path.write_text(html, encoding="utf-8")

        # Step 8: terminal summary
        all_traces = sentinel.query(limit=100)
        deny_traces = sentinel.query(policy_result=PolicyResult.DENY, limit=100)

        print("=" * 64)
        print("  SENTINEL — FULL PIPELINE RESULT")
        print("=" * 64)
        print(f"  Total traces       : {len(all_traces)}")
        print(f"  DENY traces        : {len(deny_traces)}")
        print(f"  Sovereignty score  : {runtime.sovereignty_score:.0%}")
        print(f"  CI/CD findings     : {len(cicd.findings)}")
        print(f"  Manifesto score    : {manifesto_report.overall_score:.0%}")
        print(f"  Acknowledged gaps  : {len(manifesto_report.acknowledged_gaps)}")
        print(f"  EU AI Act overall  : {compliance.overall}")
        print(f"  Automated coverage : {compliance.automated_coverage:.0%}")
        print(f"  Days to enforcement: {compliance.days_to_enforcement}")
        print(f"  HTML report        : {html_path} ({html_path.stat().st_size:,} bytes)")
        print("=" * 64)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
