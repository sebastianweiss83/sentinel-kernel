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
    from sentinel import __version__

    parser = argparse.ArgumentParser(
        prog="sentinel",
        description="Sentinel — Sovereign decision tracing for any autonomous system",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"sentinel-kernel {__version__}",
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
    p_comp = sub.add_parser("compliance", help="Compliance utilities")
    comp_sub = p_comp.add_subparsers(dest="compliance_command")
    p_check = comp_sub.add_parser("check", help="Run compliance checkers")
    p_check.add_argument("--html", action="store_true", help="Emit HTML report")
    p_check.add_argument("--json", action="store_true", help="Emit JSON report")
    p_check.add_argument("--output", help="Write output to file instead of stdout")
    p_check.add_argument(
        "--all-frameworks",
        action="store_true",
        help="Run EU AI Act + DORA + NIS2 (unified report)",
    )
    p_check.add_argument(
        "--financial-sector",
        action="store_true",
        help="Include DORA (financial sector)",
    )
    p_check.add_argument(
        "--critical-infrastructure",
        action="store_true",
        help="Include NIS2 (critical infrastructure)",
    )

    # --- dora / nis2 shortcuts ---------------------------------------------
    p_dora = sub.add_parser("dora", help="DORA compliance utilities")
    dora_sub = p_dora.add_subparsers(dest="dora_command")
    p_dora_check = dora_sub.add_parser("check", help="Run the DORA checker")
    p_dora_check.add_argument("--json", action="store_true")

    p_nis2 = sub.add_parser("nis2", help="NIS2 compliance utilities")
    nis2_sub = p_nis2.add_subparsers(dest="nis2_command")
    p_nis2_check = nis2_sub.add_parser("check", help="Run the NIS2 checker")
    p_nis2_check.add_argument("--json", action="store_true")

    # --- report -------------------------------------------------------------
    p_report = sub.add_parser("report", help="Generate a self-contained HTML sovereignty report")
    p_report.add_argument("--output", help="Write HTML to file instead of stdout")
    p_report.add_argument("--manifesto", help="Dotted path to a SentinelManifesto subclass")
    p_report.add_argument("--repo", default=".", help="Repository root")

    # --- dashboard ----------------------------------------------------------
    p_dash = sub.add_parser("dashboard", help="Live terminal dashboard")
    p_dash.add_argument("--frames", type=int, default=1, help="Number of frames to render")
    p_dash.add_argument("--interval", type=float, default=2.0, help="Seconds between frames")

    # --- verify -------------------------------------------------------------
    p_verify = sub.add_parser(
        "verify",
        help="Verify the integrity of one or all stored traces",
    )
    p_verify.add_argument("--trace-id", help="Verify a single trace by ID")
    p_verify.add_argument("--all", action="store_true", help="Verify all traces")
    p_verify.add_argument("--db", help="SQLite path (default: in-memory)")
    p_verify.add_argument("--json", action="store_true", help="Emit JSON report")

    # --- purge --------------------------------------------------------------
    p_purge = sub.add_parser(
        "purge",
        help="Remove traces older than a cutoff date",
    )
    p_purge.add_argument("--before", required=True, help="ISO date cutoff")
    p_purge.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be purged without deleting",
    )
    p_purge.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt",
    )
    p_purge.add_argument("--db", help="SQLite path (default: in-memory)")

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

    # --- attestation --------------------------------------------------------
    p_att = sub.add_parser("attestation", help="Governance attestation utilities")
    att_sub = p_att.add_subparsers(dest="attestation_command")

    p_att_gen = att_sub.add_parser("generate", help="Generate a self-contained attestation")
    p_att_gen.add_argument("--output", help="Output JSON path (default: stdout)")
    p_att_gen.add_argument("--manifesto", help="Dotted path to a SentinelManifesto subclass")
    p_att_gen.add_argument(
        "--compliance",
        action="store_true",
        help="Include an EU AI Act compliance summary",
    )

    p_att_ver = att_sub.add_parser("verify", help="Verify an attestation offline")
    p_att_ver.add_argument("--input", required=True, help="Attestation JSON path")

    # --- keygen -------------------------------------------------------------
    p_key = sub.add_parser("keygen", help="Generate a quantum-safe signing keypair")
    p_key.add_argument(
        "--algorithm",
        default="ML-DSA-65",
        choices=sorted({"ML-DSA-44", "ML-DSA-65", "ML-DSA-87"}),
    )
    p_key.add_argument(
        "--output-dir",
        default="./sentinel-keys/",
        help="Directory to write signing.key and signing.pub",
    )

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
    if args.command == "dora":
        if args.dora_command == "check":
            return _cmd_dora_check(args)
        p_dora.print_help()
        return 1
    if args.command == "nis2":
        if args.nis2_command == "check":
            return _cmd_nis2_check(args)
        p_nis2.print_help()
        return 1
    if args.command == "report":
        return _cmd_report(args)
    if args.command == "dashboard":
        return _cmd_dashboard(args)
    if args.command == "export":
        return _cmd_export(args)
    if args.command == "import":
        return _cmd_import(args)
    if args.command == "verify":
        return _cmd_verify(args)
    if args.command == "purge":
        return _cmd_purge(args)
    if args.command == "manifesto":
        if args.manifesto_command == "check":
            return _cmd_manifesto_check(args)
        p_man.print_help()
        return 1
    if args.command == "attestation":
        if args.attestation_command == "generate":
            return _cmd_attestation_generate(args)
        if args.attestation_command == "verify":
            return _cmd_attestation_verify(args)
        p_att.print_help()
        return 1
    if args.command == "keygen":
        return _cmd_keygen(args)

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

    # Create a dedicated empty temp directory for the demo. Using this as
    # repo_root for the scanners keeps `sentinel demo` O(1) regardless of
    # where the user invokes it from — we never walk their home dir.
    demo_dir = _Path(tempfile.mkdtemp(prefix="sentinel-demo-"))
    db_path = demo_dir / "demo.db"

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
    # Scope every filesystem-walking scanner to the empty demo dir so the
    # demo is fast and deterministic regardless of the caller's cwd.
    demo_root = str(demo_dir)
    print("[3/5] Running sovereignty scanners...")
    runtime = RuntimeScanner().scan()
    cicd = CICDScanner().scan(demo_root)
    print(f"      Runtime: {runtime.total_packages} packages, "
          f"score={runtime.sovereignty_score:.0%}")
    print("               (run from your project venv for full dependency scan)")
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
    html = HTMLReport().generate(sentinel, repo_root=demo_root)
    out_path, fallback_reason = _resolve_demo_output(args.output)
    out_path.write_text(html, encoding="utf-8")
    if fallback_reason is not None:
        print(f"      (CWD not writable — {fallback_reason})")
    print(f"      Wrote {out_path} ({len(html):,} bytes)")
    print()

    # Terminal summary (sovereignty widget from the live dashboard)
    print("━" * 64)
    print("  TERMINAL SUMMARY")
    print("━" * 64)
    try:
        dash = TerminalDashboard(sentinel)
        print(dash.render_once())
    except Exception as exc:
        print(f"  (dashboard render skipped: {exc})")
    print()

    # Structured completion block — what just happened, where the report
    # is, and what to do next. Designed for a first-time user who has
    # never seen Sentinel before.
    total_decisions = allow + deny
    score_pct = int(round(runtime.sovereignty_score * 100))

    def _row(label: str, detail: str, mark: str = "✓") -> str:
        # Fixed label column for visual alignment on a 64-wide block.
        return f"  {mark} {label:<32} {detail}"

    ks_row = (
        _row("Kill switch tested", "(EU AI Act Art. 14)")
        if not args.no_kill_switch
        else _row("Kill switch demo skipped", "(--no-kill-switch)", mark="·")
    )
    print("═" * 64)
    print("  SENTINEL DEMO COMPLETE")
    print("═" * 64)
    print()
    print(_row(f"{total_decisions} decisions traced", "(EU sovereign, local storage)"))
    print(ks_row)
    print(_row("Sovereignty scan", f"({score_pct}% score)"))
    print(_row(
        "EU AI Act compliance check",
        f"({compliance.overall} — {compliance.days_to_enforcement} days remaining)",
    ))
    print(_row("HTML report generated", ""))
    print()
    print(f"  Report saved: {out_path}")
    print(f"  Open it:      open '{out_path}'")
    print()
    print("  Next steps:   sentinel attestation generate")
    print("                sentinel report --output sovereignty_report.html")
    print()
    print(f"  EU AI Act enforcement: 2 August 2026 · "
          f"{compliance.days_to_enforcement} days")
    print("  If Sentinel helped you: ⭐  github.com/sebastianweiss83/sentinel-kernel")
    print("═" * 64)
    print()

    # Clean up temp database and demo dir
    import shutil as _shutil

    with contextlib.suppress(OSError):
        _shutil.rmtree(demo_dir, ignore_errors=True)

    return 0


def _bar(done: int, total: int, width: int = 40) -> None:
    """Simple inline progress bar (no rich dependency)."""
    filled = int(width * done / total)
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(f"\r      [{bar}] {done}/{total}")
    sys.stdout.flush()
    if done == total:
        sys.stdout.write("\n")


def _resolve_demo_output(
    explicit: str | None,
) -> tuple[Path, str | None]:
    """
    Pick where `sentinel demo` writes its HTML report.

    Priority:
      1. --output (honoured verbatim; caller owns any write failure)
      2. CWD / sentinel_demo_report.html — so users see the file where
         they invoked the command
      3. tempdir fallback when CWD is not writable (read-only mount,
         unusual sandboxes, etc.) — returns a human-readable reason so
         the CLI can surface it.

    Returns (resolved_path, fallback_reason_or_none).
    """
    import os
    import tempfile as _tempfile

    if explicit is not None:
        return Path(explicit).resolve(), None

    filename = "sentinel_demo_report.html"
    cwd = Path.cwd()
    if os.access(cwd, os.W_OK):
        return (cwd / filename).resolve(), None

    tmp = Path(_tempfile.gettempdir()) / filename
    return tmp.resolve(), f"writing to {tmp}"


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
    from sentinel.compliance import EUAIActChecker, UnifiedComplianceChecker

    sentinel = _make_default_sentinel()

    run_unified = args.all_frameworks or args.financial_sector or args.critical_infrastructure
    if run_unified:
        checker = UnifiedComplianceChecker(
            financial_sector=args.financial_sector or args.all_frameworks,
            critical_infrastructure=args.critical_infrastructure or args.all_frameworks,
        )
        unified = checker.check(sentinel)
        if args.html:
            if args.output:
                unified.save_html(args.output)
                print(f"Wrote {args.output}")
            else:
                print(unified._render_html())
        elif args.json:
            content = json.dumps(unified.as_dict(), indent=2, default=str)
            if args.output:
                Path(args.output).write_text(content, encoding="utf-8")
                print(f"Wrote {args.output}")
            else:
                print(content)
        else:
            content = unified.as_text()
            if args.output:
                Path(args.output).write_text(content, encoding="utf-8")
                print(f"Wrote {args.output}")
            else:
                print(content)
        return 0

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


def _cmd_dora_check(args: argparse.Namespace) -> int:
    from sentinel.compliance import DoraChecker

    sentinel = _make_default_sentinel()
    report = DoraChecker().check(sentinel)
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, default=str))
    else:
        print(report.as_text())
    return 0


def _cmd_nis2_check(args: argparse.Namespace) -> int:
    from sentinel.compliance import NIS2Checker

    sentinel = _make_default_sentinel()
    report = NIS2Checker().check(sentinel)
    if args.json:
        print(json.dumps(report.as_dict(), indent=2, default=str))
    else:
        print(report.as_text())
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


def _cmd_verify(args: argparse.Namespace) -> int:
    storage = SQLiteStorage(args.db) if args.db else SQLiteStorage(":memory:")
    storage.initialise()
    sentinel = Sentinel(storage=storage, project="verify-cli")

    results: list[dict[str, Any]] = []
    if args.trace_id:
        result = sentinel.verify_integrity(args.trace_id)
        results.append(result.to_dict())
    elif args.all:
        for trace in storage.query(limit=10_000):
            result = sentinel.verify_integrity(trace.trace_id)
            results.append(result.to_dict())
    else:
        print("verify: must pass --trace-id or --all", file=sys.stderr)
        return 2

    failed_rows = [row for row in results if not row["verified"]]
    if args.json:
        print(json.dumps({"results": results, "failed": len(failed_rows)}, indent=2))
    else:
        print(f"Verified: {len(results) - len(failed_rows)} / {len(results)}")
        for row in failed_rows:
            print(f"  FAIL {row['trace_id']}: {row['detail']}")
    return 0 if not failed_rows else 1


def _cmd_purge(args: argparse.Namespace) -> int:
    from datetime import datetime

    storage = SQLiteStorage(args.db) if args.db else SQLiteStorage(":memory:")
    storage.initialise()
    cutoff = datetime.fromisoformat(args.before)

    result = storage.purge_before(cutoff, dry_run=args.dry_run or not args.yes)
    if result.dry_run:
        print(f"DRY RUN — would purge {result.traces_affected} traces before {cutoff}")
        print("  Re-run with --yes to actually delete.")
    else:
        print(f"Purged {result.traces_affected} traces before {cutoff}")
    if result.oldest_remaining is not None:
        print(f"  Oldest remaining: {result.oldest_remaining.isoformat()}")
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


def _cmd_keygen(args: argparse.Namespace) -> int:
    try:
        from sentinel.crypto import QuantumSafeSigner
    except ImportError as exc:  # pragma: no cover - only fires on truly broken install
        print(str(exc), file=sys.stderr)
        return 2
    try:
        QuantumSafeSigner.generate_keypair(
            output_dir=args.output_dir,
            algorithm=args.algorithm,
        )
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:  # pragma: no cover - argparse choices prevents this
        print(f"keygen: {exc}", file=sys.stderr)
        return 2
    return 0


def _cmd_attestation_generate(args: argparse.Namespace) -> int:
    from sentinel.core.attestation import generate_attestation

    sentinel = _make_default_sentinel()
    manifesto_cls = _load_manifesto(args.manifesto) if args.manifesto else None
    manifesto = manifesto_cls() if manifesto_cls is not None else None

    compliance_report = None
    if args.compliance:
        from sentinel.compliance import EUAIActChecker

        compliance_report = EUAIActChecker().check(sentinel)

    doc = generate_attestation(
        sentinel=sentinel,
        manifesto=manifesto,
        compliance_report=compliance_report,
    )
    content = json.dumps(doc, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(content + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(content)
    return 0


def _cmd_attestation_verify(args: argparse.Namespace) -> int:
    from sentinel.core.attestation import verify_attestation

    path = Path(args.input)
    if not path.exists():
        print(f"attestation: file not found: {path}", file=sys.stderr)
        return 2
    doc = json.loads(path.read_text(encoding="utf-8"))
    result = verify_attestation(doc)
    print(f"valid:          {result.valid}")
    print(f"hash_verified:  {result.hash_verified}")
    print(f"detail:         {result.detail}")
    if result.what_failed:
        print(f"what_failed:    {result.what_failed}")
    return 0 if result.valid else 1


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
