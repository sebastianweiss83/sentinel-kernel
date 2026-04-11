"""
sentinel.cli
~~~~~~~~~~~~
Command-line interface for Sentinel.

Commands:
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

    # --- scan ---------------------------------------------------------------
    p_scan = sub.add_parser("scan", help="Run the sovereignty scanner")
    p_scan.add_argument("--runtime", action="store_true", help="Only scan runtime packages")
    p_scan.add_argument("--cicd", action="store_true", help="Only scan CI/CD config")
    p_scan.add_argument("--infra", action="store_true", help="Only scan infrastructure config")
    p_scan.add_argument("--all", action="store_true", help="Run all scanners (default)")
    p_scan.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    p_scan.add_argument("--repo", default=".", help="Repository root for CI/CD and infra scans")

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

    # --- manifesto check ----------------------------------------------------
    p_man = sub.add_parser("manifesto", help="Manifesto utilities")
    man_sub = p_man.add_subparsers(dest="manifesto_command")
    p_mcheck = man_sub.add_parser("check", help="Check a manifesto against reality")
    p_mcheck.add_argument("module", help="Dotted path OR file path to a SentinelManifesto subclass")
    p_mcheck.add_argument("--json", action="store_true", help="Emit JSON")
    p_mcheck.add_argument("--repo", default=".", help="Repository root")

    args = parser.parse_args(argv)

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


def _cmd_scan(args: argparse.Namespace) -> int:
    from sentinel.scanner import (
        CICDScanner,
        InfrastructureScanner,
        RuntimeScanner,
    )

    run_all = args.all or not (args.runtime or args.cicd or args.infra)
    out: dict[str, Any] = {}

    if args.runtime or run_all:
        out["runtime"] = RuntimeScanner().scan().to_dict()
    if args.cicd or run_all:
        out["cicd"] = CICDScanner().scan(args.repo).to_dict()
    if args.infra or run_all:
        out["infrastructure"] = InfrastructureScanner().scan(args.repo).to_dict()

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        _print_scan_text(out)
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


if __name__ == "__main__":
    raise SystemExit(main())
