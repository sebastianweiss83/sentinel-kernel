"""
sentinel.cli
~~~~~~~~~~~~
Command-line interface for Sentinel.

Commands:
    sentinel demo                 — full end-to-end demo (no Docker)
    sentinel scan                 — run the sovereignty scanner
    sentinel compliance check     — run the EU AI Act checker
    sentinel report               — generate an HTML sovereignty report
    sentinel dashboard            — live terminal dashboard
    sentinel manifesto check      — run a manifesto against reality
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from sentinel import DataResidency, Sentinel
from sentinel.storage import SQLiteStorage


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sentinel",
        description="Sentinel — EU-sovereign AI decision middleware",
    )
    sub = parser.add_subparsers(dest="command")

    # --- demo ---------------------------------------------------------------
    p_demo = sub.add_parser("demo", help="Run the full end-to-end demo (no Docker)")
    p_demo.add_argument(
        "--output",
        default=None,
        help=(
            "Output path for the generated HTML report. "
            "Defaults to a tempfile under the OS temp dir."
        ),
    )
    p_demo.add_argument(
        "--no-kill-switch",
        action="store_true",
        help="Skip the kill-switch demonstration",
    )

    # --- scan ---------------------------------------------------------------
    p_scan = sub.add_parser("scan", help="Run the sovereignty scanner")
    p_scan.add_argument("--runtime", action="store_true", help="Only scan runtime packages")
    p_scan.add_argument("--cicd", action="store_true", help="Only scan CI/CD config")
    p_scan.add_argument("--infra", action="store_true", help="Only scan infrastructure config")
    p_scan.add_argument("--all", action="store_true", help="Run all scanners (default)")
    p_scan.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    p_scan.add_argument("--repo", default=".", help="Repository root for CI/CD and infra scans")
    p_scan.add_argument(
        "--suggest-alternatives",
        action="store_true",
        help="Show EU-sovereign alternatives for each flagged US package",
    )

    # --- compliance check ---------------------------------------------------
    p_comp = sub.add_parser("compliance", help="EU AI Act compliance utilities")
    comp_sub = p_comp.add_subparsers(dest="compliance_command")
    p_check = comp_sub.add_parser("check", help="Run the EU AI Act automated checker")
    p_check.add_argument("--html", action="store_true", help="Emit HTML report")
    p_check.add_argument("--json", action="store_true", help="Emit JSON report")
    p_check.add_argument("--output", help="Write output to file instead of stdout")

    # --- report -------------------------------------------------------------
    p_report = sub.add_parser("report", help="Generate a self-contained HTML sovereignty report")
    p_report.add_argument("--output", help="Write HTML to file instead of stdout")
    p_report.add_argument("--manifesto", help="Dotted path to a SentinelManifesto subclass")
    p_report.add_argument("--repo", default=".", help="Repository root")

    # --- dashboard ----------------------------------------------------------
    p_dash = sub.add_parser("dashboard", help="Live terminal dashboard")
    p_dash.add_argument("--frames", type=int, default=1, help="Number of frames to render")
    p_dash.add_argument("--interval", type=float, default=2.0, help="Seconds between frames")

    # --- export / import ----------------------------------------------------
    p_export = sub.add_parser("export", help="Export traces to NDJSON")
    p_export.add_argument("--output", required=True, help="Output NDJSON path")
    p_export.add_argument("--agent", help="Filter by agent name")
    p_export.add_argument("--project", help="Filter by project")
    p_export.add_argument("--since", help="ISO date — only traces started at or after")
    p_export.add_argument("--until", help="ISO date — only traces started before")
    p_export.add_argument("--db", help="SQLite path (default: in-memory for CLI)")

    p_import = sub.add_parser("import", help="Import traces from NDJSON")
    p_import.add_argument("--input", required=True, help="Input NDJSON path")
    p_import.add_argument("--db", help="SQLite path (default: in-memory for CLI)")

    # --- manifesto check ----------------------------------------------------
    p_man = sub.add_parser("manifesto", help="Manifesto utilities")
    man_sub = p_man.add_subparsers(dest="manifesto_command")
    p_mcheck = man_sub.add_parser("check", help="Check a manifesto against reality")
    p_mcheck.add_argument("module", help="Dotted path OR file path to a SentinelManifesto subclass")
    p_mcheck.add_argument("--json", action="store_true", help="Emit JSON")
    p_mcheck.add_argument("--repo", default=".", help="Repository root")

    args = parser.parse_args(argv)

    if args.command == "demo":
        return _cmd_demo(args)
    if args.command == "scan":
        return _cmd_scan(args)
    if args.command == "compliance":
        if args.compliance_command == "check":
            return _cmd_compliance_check(args)
        p_comp.print_help()
        return 1
    if args.command == "report":
        return _cmd_report(args)
    if args.command == "dashboard":
        return _cmd_dashboard(args)
    if args.command == "export":
        return _cmd_export(args)
    if args.command == "import":
        return _cmd_import(args)
    if args.command == "manifesto":
        if args.manifesto_command == "check":
            return _cmd_manifesto_check(args)
        p_man.print_help()
        return 1

    parser.print_help()
    return 1


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _cmd_demo(args: argparse.Namespace) -> int:
    """
    Run an end-to-end demo:
      - 50 realistic decisions with a policy evaluator
      - kill-switch demonstration (5 blocked calls)
      - runtime & CI/CD sovereignty scanners
      - EU AI Act automated check
      - self-contained HTML report
      - terminal summary

    Exits 0 on success. Temp database is cleaned up automatically.
    """
    import contextlib
    import random
    import tempfile
    from pathlib import Path as _Path

    from sentinel.compliance import EUAIActChecker
    from sentinel.dashboard import HTMLReport, TerminalDashboard
    from sentinel.policy.evaluator import SimpleRuleEvaluator
    from sentinel.scanner import CICDScanner, RuntimeScanner

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = _Path(tmp.name)

    print("━" * 64)
    print("  SENTINEL DEMO — End-to-end sovereignty walkthrough")
    print("━" * 64)
    print(f"  Temp database: {db_path}")
    print()

    def _policy(inputs: dict[str, Any]) -> tuple[bool, str | None]:
        req = inputs.get("request", {})
        amount = req.get("amount", 0)
        if amount > 10_000:
            return False, "amount_exceeds_cap"
        return True, None

    sentinel = Sentinel(
        storage=SQLiteStorage(str(db_path)),
        project="sentinel-demo",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator({"policies/approval.py": _policy}),
    )

    @sentinel.trace(policy="policies/approval.py")
    def approve(request: dict[str, Any]) -> dict[str, Any]:
        return {"decision": "approved", "amount": request["amount"]}

    # Scenario 1: 50 realistic decisions
    print("[1/5] Running 50 realistic decisions...")
    rng = random.Random(42)
    allow = deny = 0
    for i in range(50):
        amount = int(rng.triangular(100, 25_000, 5_000))
        try:
            approve(request={"amount": amount, "requester": f"user{i}"})
            allow += 1
        except Exception:
            deny += 1
        _bar(i + 1, 50)
    print(f"      ALLOW: {allow} · DENY: {deny}")
    print()

    # Scenario 2: Kill switch
    if not args.no_kill_switch:
        print("[2/5] Engaging kill switch (EU AI Act Art. 14)...")
        sentinel.engage_kill_switch("demo halt")
        blocked = 0
        for i in range(5):
            try:
                approve(request={"amount": 1000, "requester": f"halted{i}"})
            except Exception:
                blocked += 1
        print(f"      Blocked {blocked} calls while engaged")
        sentinel.disengage_kill_switch("demo resume")
        print("      Kill switch disengaged")
        print()
    else:
        print("[2/5] (kill-switch demo skipped)")
        print()

    # Scenario 3: Sovereignty scanners
    print("[3/5] Running sovereignty scanners...")
    runtime = RuntimeScanner().scan()
    cicd = CICDScanner().scan(".")
    print(f"      Runtime: {runtime.total_packages} packages, "
          f"score={runtime.sovereignty_score:.0%}")
    print(f"      CI/CD:   {len(cicd.findings)} findings")
    print()

    # Scenario 4: EU AI Act compliance
    print("[4/5] Running EU AI Act compliance checker...")
    compliance = EUAIActChecker().check(sentinel)
    print(f"      Overall: {compliance.overall}")
    print(f"      Automated coverage: {compliance.automated_coverage:.0%}")
    print(f"      Days to enforcement: {compliance.days_to_enforcement}")
    print()

    # Scenario 5: HTML report
    print("[5/5] Generating HTML sovereignty report...")
    html = HTMLReport().generate(sentinel, repo_root=".")
    if args.output is None:
        out_path = _Path(tempfile.gettempdir()) / "sentinel_demo_report.html"
    else:
        out_path = _Path(args.output)
    out_path = out_path.resolve()
    out_path.write_text(html, encoding="utf-8")
    print(f"      Wrote {out_path} ({len(html):,} bytes)")
    print()

    # Terminal summary
    print("━" * 64)
    print("  TERMINAL SUMMARY")
    print("━" * 64)
    try:
        dash = TerminalDashboard(sentinel)
        print(dash.render_once())
    except Exception as exc:
        print(f"  (dashboard render skipped: {exc})")
    print()

    print(f"✓ Report saved: {out_path}")
    print()

    # Clean up temp database
    with contextlib.suppress(OSError):
        db_path.unlink(missing_ok=True)

    return 0


def _bar(done: int, total: int, width: int = 40) -> None:
    """Simple inline progress bar (no rich dependency)."""
    filled = int(width * done / total)
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(f"\r      [{bar}] {done}/{total}")
    sys.stdout.flush()
    if done == total:
        sys.stdout.write("\n")


def _cmd_scan(args: argparse.Namespace) -> int:
    from sentinel.scanner import (
        CICDScanner,
        InfrastructureScanner,
        RuntimeScanner,
    )

    run_all = args.all or not (args.runtime or args.cicd or args.infra)
    out: dict[str, Any] = {}
    alternatives: dict[str, str] = {}

    if args.runtime or run_all:
        runtime_result = RuntimeScanner().scan()
        out["runtime"] = runtime_result.to_dict()
        if args.suggest_alternatives:
            alternatives = runtime_result.sovereign_alternatives()
    if args.cicd or run_all:
        out["cicd"] = CICDScanner().scan(args.repo).to_dict()
    if args.infra or run_all:
        out["infrastructure"] = InfrastructureScanner().scan(args.repo).to_dict()

    if args.json:
        if args.suggest_alternatives:
            out["eu_alternatives"] = alternatives
        print(json.dumps(out, indent=2))
    else:
        _print_scan_text(out)
        if args.suggest_alternatives and alternatives:
            print()
            print("EU-SOVEREIGN ALTERNATIVES")
            print("-------------------------")
            for pkg, alt in sorted(alternatives.items()):
                print(f"  {pkg} → {alt}")
    return 0


def _print_scan_text(out: dict[str, Any]) -> None:
    if "runtime" in out:
        rt = out["runtime"]
        print(f"RUNTIME  {rt['total_packages']} packages  "
              f"score={rt['sovereignty_score']:.0%}  "
              f"us_owned={rt['us_owned_packages']}  "
              f"unknown={rt['unknown_jurisdiction']}")
        if rt["critical_path_violations"]:
            print("  CRITICAL PATH VIOLATIONS:")
            for v in rt["critical_path_violations"]:
                print(f"    - {v}")
    if "cicd" in out:
        c = out["cicd"]
        print(f"CI/CD    {c['files_scanned']} files, {c['total_findings']} findings, "
              f"us_controlled={c['us_controlled_components']}")
    if "infrastructure" in out:
        i = out["infrastructure"]
        print(f"INFRA    {i['files_scanned']} files, {i['total_findings']} findings, "
              f"us_controlled={i['us_controlled_components']}")


def _cmd_compliance_check(args: argparse.Namespace) -> int:
    from sentinel.compliance import EUAIActChecker

    sentinel = _make_default_sentinel()
    report = EUAIActChecker().check(sentinel)

    if args.html:
        content = report.as_html()
    elif args.json:
        content = json.dumps(report.as_json(), indent=2)
    else:
        content = report.as_text()

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(content)
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from sentinel.dashboard import HTMLReport

    sentinel = _make_default_sentinel()
    manifesto = _load_manifesto(args.manifesto) if args.manifesto else None
    html = HTMLReport().generate(
        sentinel,
        manifesto=manifesto() if manifesto else None,
        repo_root=args.repo,
    )

    if args.output:
        Path(args.output).write_text(html, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(html)
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    from datetime import datetime

    storage = SQLiteStorage(args.db) if args.db else SQLiteStorage(":memory:")
    storage.initialise()
    start = datetime.fromisoformat(args.since) if args.since else None
    end = datetime.fromisoformat(args.until) if args.until else None
    count = storage.export_ndjson(
        args.output,
        start=start,
        end=end,
        agent=args.agent,
        project=args.project,
    )
    print(f"Exported {count} traces to {args.output}")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    storage = SQLiteStorage(args.db) if args.db else SQLiteStorage(":memory:")
    storage.initialise()
    imported, skipped = storage.import_ndjson(args.input)
    print(f"Imported {imported} traces, skipped {skipped} duplicates")
    return 0


def _cmd_dashboard(args: argparse.Namespace) -> int:
    from sentinel.dashboard import TerminalDashboard

    sentinel = _make_default_sentinel()
    dash = TerminalDashboard(sentinel)
    if args.frames == 1:
        print(dash.render_once())
    else:
        dash.run(interval_s=args.interval, max_frames=args.frames)
    return 0


def _cmd_manifesto_check(args: argparse.Namespace) -> int:
    cls = _load_manifesto(args.module)
    if cls is None:
        print(f"Could not resolve manifesto: {args.module}", file=sys.stderr)
        return 2

    sentinel = _make_default_sentinel()
    report = cls().check(sentinel=sentinel, repo_root=args.repo)
    if args.json:
        print(report.as_json())
    else:
        print(report.as_text())
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_default_sentinel() -> Sentinel:
    """Build a default in-memory Sentinel for CLI commands."""
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="sentinel-cli",
        data_residency=DataResidency.LOCAL,
    )


def _load_manifesto(ref: str) -> Any:
    """
    Load a SentinelManifesto subclass from a dotted module path or file path.

    Accepts::

        my_package.my_module:ManifestoClass
        path/to/file.py:ManifestoClass
    """
    from sentinel.manifesto import SentinelManifesto

    if ":" not in ref:
        return None
    module_ref, class_name = ref.rsplit(":", 1)

    if module_ref.endswith(".py") or "/" in module_ref:
        path = Path(module_ref)
        if not path.exists():
            return None
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = __import__(module_ref, fromlist=[class_name])

    cls = getattr(module, class_name, None)
    if cls is None:
        return None
    if isinstance(cls, type) and issubclass(cls, SentinelManifesto):
        return cls
    return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
