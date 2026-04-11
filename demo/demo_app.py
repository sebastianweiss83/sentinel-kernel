"""
demo/demo_app.py
~~~~~~~~~~~~~~~~
Realistic Sentinel demonstrator for a fictional EU defence contractor.

Runs three scenarios:
  A) Autonomous procurement approval (policy eval + kill switch)
  B) LangChain-style document analysis (mocked, no API keys)
  C) Sovereignty scan + manifesto report + EU AI Act diff

Works offline. No API keys required. OTel endpoint is optional —
if unreachable, the demo logs a warning and continues. Local storage
and audit trail are always written first.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from sentinel import DataResidency, KillSwitchEngaged, PolicyDeniedError, Sentinel
from sentinel.compliance import EUAIActChecker
from sentinel.dashboard import HTMLReport, TerminalDashboard
from sentinel.manifesto import (
    EUOnly,
    OnPremiseOnly,
    Required,
    SentinelManifesto,
    Targeting,
    ZeroExposure,
)
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.scanner import (
    CICDScanner,
    InfrastructureScanner,
    RuntimeScanner,
)
from sentinel.storage import SQLiteStorage

# ---------------------------------------------------------------------------
# Manifesto: what this organisation demands
# ---------------------------------------------------------------------------


class DefenceContractor(SentinelManifesto):
    jurisdiction = EUOnly()
    cloud_act = ZeroExposure()
    kill_switch = Required()
    airgap = Required()
    storage = OnPremiseOnly(country="DE")
    bsi = Targeting(by="2026-12-31")


# ---------------------------------------------------------------------------
# Scenario A: procurement approval
# ---------------------------------------------------------------------------


def scenario_a_procurement(sentinel: Sentinel) -> None:
    print("=" * 70)
    print("  Scenario A — Autonomous procurement approval")
    print("=" * 70)

    @sentinel.trace(policy="policies/procurement.py")
    async def approve(request: dict) -> dict:
        await asyncio.sleep(0.01)
        return {
            "request_id": request["id"],
            "status": "approved",
            "amount": request["amount"],
        }

    requests = [
        {"id": "req-1", "amount": 5_000, "vendor": "Acme GmbH"},
        {"id": "req-2", "amount": 99_000, "vendor": "Bosch SE"},
        {"id": "req-3", "amount": 8_500, "vendor": "STACKIT"},
    ]

    for req in requests:
        try:
            result = asyncio.run(approve(request=req))
            print(f"  ALLOW  {result['request_id']} ({req['amount']} EUR)")
        except PolicyDeniedError:
            print(f"  DENY   {req['id']} — exceeded procurement cap")

    # Halt mid-run to demonstrate Art. 14
    print("  -> engaging kill switch (simulated human halt)")
    sentinel.engage_kill_switch("operator halted procurement pipeline for audit")
    blocked = 0
    for req in [{"id": "req-4", "amount": 100, "vendor": "x"}]:
        try:
            asyncio.run(approve(request=req))
        except KillSwitchEngaged:
            blocked += 1
            print(f"  BLOCK  {req['id']} — kill switch engaged")

    print("  -> disengaging kill switch (audit complete)")
    sentinel.disengage_kill_switch("audit complete")
    asyncio.run(approve(request={"id": "req-5", "amount": 2_000, "vendor": "Scaleway"}))
    print("  ALLOW  req-5 — normal operation resumed")
    print(f"  Scenario A complete — {blocked} blocked call(s) recorded as DENY traces.")
    print()


# ---------------------------------------------------------------------------
# Scenario B: document analysis via a mocked LangChain chain
# ---------------------------------------------------------------------------


def scenario_b_document_analysis(sentinel: Sentinel) -> None:
    print("=" * 70)
    print("  Scenario B — Document analysis (LangChain-style, mocked LLM)")
    print("=" * 70)

    @sentinel.trace
    def classify_document(title: str, text: str) -> dict:
        # Mocked LLM: simple heuristic, no API call
        classification = "CLASSIFIED" if "weapon" in text.lower() else "UNCLASSIFIED"
        return {
            "title": title,
            "classification": classification,
            "model": "mock-llm/1.0",
        }

    docs = [
        ("Procurement report 2026-Q1", "routine supplier review and pricing"),
        ("Weapon systems inventory",   "current weapon stock and maintenance schedule"),
        ("HR quarterly",               "staffing summary and benefits review"),
    ]
    for title, text in docs:
        result = classify_document(title, text)
        print(f"  {result['classification']:<14} {title}")
    print("  Scenario B complete — traces flow to local storage and OTel (if reachable).")
    print()


# ---------------------------------------------------------------------------
# Scenario C: sovereignty report
# ---------------------------------------------------------------------------


def scenario_c_sovereignty_report(sentinel: Sentinel, output_dir: Path) -> None:
    print("=" * 70)
    print("  Scenario C — Sovereignty + EU AI Act report")
    print("=" * 70)

    runtime = RuntimeScanner().scan()
    cicd = CICDScanner().scan(".")
    infra = InfrastructureScanner().scan(".")
    print(f"  Runtime packages : {runtime.total_packages}")
    print(f"  Sovereignty score: {runtime.sovereignty_score:.0%}")
    print(f"  US-owned         : {runtime.us_owned_packages}")
    print(f"  CI/CD findings   : {len(cicd.findings)}")
    print(f"  Infra findings   : {len(infra.findings)}")

    report = DefenceContractor().check(
        sentinel=sentinel,
        runtime_scan=runtime,
        cicd_scan=cicd,
        infra_scan=infra,
    )
    print()
    print(f"  Manifesto score  : {report.overall_score:.0%}")
    print(f"  Gaps             : {len(report.gaps)}")
    print(f"  Acknowledged gaps: {len(report.acknowledged_gaps)}")
    print(f"  Days to enforce  : {report.days_to_enforcement}")

    compliance = EUAIActChecker().check(sentinel)
    print()
    print(f"  EU AI Act overall : {compliance.overall}")
    print(f"  Automated coverage: {compliance.automated_coverage:.0%}")

    # Write self-contained HTML report
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "sovereignty_report.html"
    html = HTMLReport().generate(sentinel, manifesto=DefenceContractor())
    html_path.write_text(html, encoding="utf-8")
    print(f"  Wrote {html_path}")

    manifesto_json = output_dir / "manifesto.json"
    report.export_json(manifesto_json)
    print(f"  Wrote {manifesto_json}")
    print()


# ---------------------------------------------------------------------------
# OTel wiring (optional)
# ---------------------------------------------------------------------------


def maybe_wire_otel(sentinel: Sentinel) -> None:
    endpoint = os.environ.get("OTEL_ENDPOINT")
    if not endpoint:
        print("  (OTEL_ENDPOINT not set — skipping OTel export)")
        return
    try:
        from sentinel.integrations.otel import OTelExporter
        OTelExporter(sentinel, endpoint=endpoint, service_name="sentinel-demo")
        print(f"  OTel exporter wired to {endpoint}")
    except ImportError as exc:
        print(f"  OTel extra not installed: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"  OTel wiring failed (local storage continues): {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    output_dir = Path("./demo-output")
    db_path = output_dir / "sentinel-demo.db"
    output_dir.mkdir(parents=True, exist_ok=True)

    def procurement_policy(inputs: dict) -> tuple[bool, str | None]:
        req = inputs.get("request", {})
        if req.get("amount", 0) > 50_000:
            return False, "procurement_cap_exceeded"
        return True, None

    sentinel = Sentinel(
        storage=SQLiteStorage(str(db_path)),
        project=os.environ.get("SENTINEL_PROJECT", "sentinel-demo"),
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator(
            {"policies/procurement.py": procurement_policy}
        ),
    )

    print()
    print("=" * 70)
    print("  SENTINEL DEMO")
    print("  EU-sovereign AI decision middleware — Defence contractor profile")
    print("=" * 70)
    maybe_wire_otel(sentinel)
    print()

    scenario_a_procurement(sentinel)
    scenario_b_document_analysis(sentinel)
    scenario_c_sovereignty_report(sentinel, output_dir)

    # Final frame from the terminal dashboard
    print(TerminalDashboard(sentinel).render_once())

    # Final query summary
    traces = sentinel.query(limit=1000)
    print()
    print(f"  Total traces written: {len(traces)}")
    print(f"  SQLite database: {db_path}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
