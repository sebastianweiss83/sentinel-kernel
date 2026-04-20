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
from datetime import datetime
from pathlib import Path
from typing import Any

from sentinel import DataResidency, PolicyDeniedError, Sentinel
from sentinel.storage import SQLiteStorage


def main(argv: list[str] | None = None) -> int:
    from sentinel import __version__

    parser = argparse.ArgumentParser(
        prog="sentinel",
        description=(
            "Sentinel — Sovereign decision trace and policy enforcement layer "
            "for autonomous systems. Supports EU AI Act Art. 12/13/14/17 "
            "evidence. Not a full compliance solution."
        ),
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

    # --- comply — PAdES PDF sign / verify -----------------------------------
    p_comply = sub.add_parser(
        "comply",
        help="PAdES PDF signing and verification (v3.4)",
    )
    comply_sub = p_comply.add_subparsers(dest="comply_command")
    p_comply_sign = comply_sub.add_parser(
        "sign",
        help="PAdES-sign an evidence-pack PDF",
    )
    p_comply_sign.add_argument("input", help="Path to the PDF to sign")
    p_comply_sign.add_argument(
        "--output",
        default=None,
        help="Output path (default: <input>.signed.pdf)",
    )
    p_comply_sign.add_argument(
        "--reason",
        default="Sentinel evidence pack signature",
        help="PAdES signature reason field",
    )
    p_comply_verify = comply_sub.add_parser(
        "verify",
        help="Verify the PAdES signature(s) on a PDF",
    )
    p_comply_verify.add_argument("input", help="Path to the signed PDF")
    p_comply_verify.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output",
    )

    # --- chain — attestation hash-chain verification ------------------------
    p_chain = sub.add_parser(
        "chain",
        help="Attestation hash-chain verification (v3.4)",
    )
    chain_sub = p_chain.add_subparsers(dest="chain_command")
    p_chain_verify = chain_sub.add_parser(
        "verify",
        help="Verify a chain of attestations from a JSON file",
    )
    p_chain_verify.add_argument(
        "input",
        help=(
            "Path to a JSON file containing a list of attestations "
            "(ordered genesis-first)"
        ),
    )
    p_chain_verify.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output",
    )

    # --- key — Ed25519 default attestation signing --------------------------
    p_ed_key = sub.add_parser(
        "key",
        help="Manage the default Ed25519 attestation signing key",
    )
    ed_key_sub = p_ed_key.add_subparsers(dest="key_command")
    p_ed_init = ed_key_sub.add_parser(
        "init",
        help="Create the default Ed25519 key if it does not exist",
    )
    p_ed_init.add_argument(
        "--path",
        default=None,
        help=(
            "Override key path (default: $SENTINEL_KEY_PATH or "
            "~/.sentinel/ed25519.key)"
        ),
    )
    p_ed_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing key at the target path",
    )
    p_ed_where = ed_key_sub.add_parser(
        "path",
        help="Print the resolved default Ed25519 key path",
    )
    p_ed_pub = ed_key_sub.add_parser(
        "public",
        help="Print the PEM-encoded Ed25519 public key",
    )
    p_ed_pub.add_argument(
        "--path",
        default=None,
        help="Override key path",
    )

    # --- manifesto check ----------------------------------------------------
    p_man = sub.add_parser("manifesto", help="Manifesto utilities")
    man_sub = p_man.add_subparsers(dest="manifesto_command")
    p_mcheck = man_sub.add_parser("check", help="Check a manifesto against reality")
    p_mcheck.add_argument("module", help="Dotted path OR file path to a SentinelManifesto subclass")
    p_mcheck.add_argument("--json", action="store_true", help="Emit JSON")
    p_mcheck.add_argument("--repo", default=".", help="Repository root")

    # --- ci-check -----------------------------------------------------------
    p_ci = sub.add_parser(
        "ci-check",
        help="One-stop CI/CD check — EU AI Act + sovereignty scan + optional manifesto",
    )
    p_ci.add_argument(
        "--manifesto",
        default=None,
        help="Optional manifesto reference (module:Class or path.py:Class)",
    )
    p_ci.add_argument("--repo", default=".", help="Repository root for manifesto check")
    p_ci.add_argument("--json", action="store_true", help="Emit JSON instead of text")

    # --- quickstart ---------------------------------------------------------
    p_qs = sub.add_parser(
        "quickstart",
        help="Scaffold a local pilot: hello_sentinel.py + ./.sentinel/",
    )
    p_qs.add_argument(
        "--force",
        action="store_true",
        help="Regenerate hello_sentinel.py even if it already exists",
    )

    # --- status -------------------------------------------------------------
    p_status = sub.add_parser(
        "status",
        help="Show pilot activity, sovereignty, and audit readiness",
    )
    p_status.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of text",
    )

    # --- audit-gap ----------------------------------------------------------
    p_ag = sub.add_parser(
        "audit-gap",
        help="Show what else your auditor will ask for (audit readiness score)",
    )
    p_ag.add_argument(
        "--profile",
        default="default",
        choices=sorted({"default", "landesbank", "insurer", "public-sector"}),
        help="Sector profile (default: default)",
    )
    p_ag.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of text",
    )

    # --- fix ----------------------------------------------------------------
    p_fix = sub.add_parser(
        "fix",
        help="Close library-level audit-gap items",
    )
    fix_sub = p_fix.add_subparsers(dest="fix_command")
    p_fix_ks = fix_sub.add_parser(
        "kill-switch",
        help="Register an Art. 14 kill switch handler",
    )
    p_fix_ks.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of text",
    )
    p_fix_ret = fix_sub.add_parser(
        "retention",
        help="Record a retention policy for the trace record",
    )
    p_fix_ret.add_argument(
        "--days",
        type=int,
        default=2555,
        help="Retention days (default: 2555, ~7 years)",
    )
    p_fix_ret.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of text",
    )

    # --- evidence-pack ------------------------------------------------------
    p_ep = sub.add_parser(
        "evidence-pack",
        help="Generate a signed PDF evidence pack for auditors",
    )
    p_ep.add_argument(
        "--output",
        default=None,
        help="Output PDF path (default: audit.pdf in the current directory)",
    )
    p_ep.add_argument("--since", help="ISO 8601 — window start (default: no lower bound)")
    p_ep.add_argument("--until", help="ISO 8601 — window end (default: no upper bound)")
    p_ep.add_argument("--project", help="Filter by project name")
    p_ep.add_argument(
        "--financial-sector",
        action="store_true",
        help="Include the DORA section",
    )
    p_ep.add_argument(
        "--critical-infrastructure",
        action="store_true",
        help="Include the NIS2 section",
    )
    p_ep.add_argument(
        "--max-traces",
        type=int,
        default=10_000,
        help="Maximum number of traces to include (default 10000)",
    )
    p_ep.add_argument("--db", help="SQLite path (default: in-memory)")
    p_ep.add_argument(
        "--manifesto",
        default=None,
        help="Optional manifesto reference (module:Class or path.py:Class)",
    )
    p_ep.add_argument(
        "--title",
        default="Sentinel Evidence Pack",
        help="Pack title used on the cover page",
    )

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
    if args.command == "chain":
        if args.chain_command == "verify":
            return _cmd_chain_verify(args)
        p_chain.print_help()
        return 1
    if args.command == "comply":
        if args.comply_command == "sign":
            return _cmd_comply_sign(args)
        if args.comply_command == "verify":
            return _cmd_comply_verify(args)
        p_comply.print_help()
        return 1
    if args.command == "key":
        if args.key_command == "init":
            return _cmd_key_init(args)
        if args.key_command == "path":
            return _cmd_key_path(args)
        if args.key_command == "public":
            return _cmd_key_public(args)
        p_ed_key.print_help()
        return 1
    if args.command == "ci-check":
        return _cmd_ci_check(args)
    if args.command == "evidence-pack":
        return _cmd_evidence_pack(args)
    if args.command == "quickstart":
        return _cmd_quickstart(args)
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "audit-gap":
        return _cmd_audit_gap(args)
    if args.command == "fix":
        if args.fix_command == "kill-switch":
            return _cmd_fix_kill_switch(args)
        if args.fix_command == "retention":
            return _cmd_fix_retention(args)
        p_fix.print_help()
        return 1

    parser.print_help()
    return 1


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def _open_hint(path: Any) -> str:
    """
    Return a platform-appropriate command string to open a local file.

    Used by every CLI command that writes a human-viewable artefact so
    the user sees a copy-pasteable next step after the ``Wrote <path>``
    line. Matches the UX pattern introduced in v3.0.3 for
    ``sentinel demo`` and generalised across all file-producing
    commands in v3.1.x.

    Behaviour per platform (from ``sys.platform``):

    - ``darwin`` → ``open '<path>'``
    - ``win32``  → ``start "" "<path>"``
    - anything else (Linux, BSD, …) → ``xdg-open '<path>'``

    The path is shell-quoted so paths with spaces work unchanged.
    """
    path_str = str(path)
    if sys.platform == "darwin":
        return f"open '{path_str}'"
    if sys.platform == "win32":
        return f'start "" "{path_str}"'
    return f"xdg-open '{path_str}'"


def _print_open_hint(path: Any) -> None:
    """Print a one-line indented open hint after a ``Wrote`` line."""
    print(f"  → {_open_hint(path)}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


_DEMO_SCENARIOS: tuple[tuple[str, int, bool], ...] = (
    # (label, amount EUR, dual_use classification)
    ("Standard component export (civilian use)",       4_200,  False),
    ("Spare parts (allied military logistics)",       12_000,  False),
    ("Medical supplies (humanitarian shipment)",       8_700,  False),
    ("High-value dual-use electronics export",       890_000,  True),   # BLOCKED
    ("Routine training equipment",                     6_500,  False),
    ("Replacement avionics (certified civilian)",     45_000,  False),
    ("Encrypted comms equipment (dual-use)",         220_000,  True),   # BLOCKED
    ("Sensor array (weather application)",            31_000,  False),
    ("Surveillance optics (dual-use)",               150_000,  True),   # BLOCKED
    ("Standard power supplies",                        3_400,  False),
)


def _cmd_demo(args: argparse.Namespace) -> int:
    """
    Narrative end-to-end demo.

    Walks ten concrete export-approval decisions for a defence-logistics
    AI agent. Three are blocked by policy (single-transaction cap or
    dual-use review threshold). Every decision lands in the immutable
    audit trail. Then: kill switch, sovereignty scan, EU AI Act check,
    self-contained HTML report.

    Exits 0 on success. Temp database is cleaned up automatically.
    """
    import contextlib
    import tempfile
    from pathlib import Path as _Path

    from sentinel.compliance import EUAIActChecker
    from sentinel.dashboard import HTMLReport, TerminalDashboard
    from sentinel.policy.evaluator import SimpleRuleEvaluator
    from sentinel.scanner import CICDScanner, RuntimeScanner

    # Dedicated temp dir so scanners never walk the caller's home.
    demo_dir = _Path(tempfile.mkdtemp(prefix="sentinel-demo-"))
    db_path = demo_dir / "demo.db"

    print("━" * 64)
    print("  SENTINEL DEMO — Defence logistics export-approval walkthrough")
    print("━" * 64)
    print("  Scenario: an AI agent triages export-approval requests.")
    print("  Policy:   single-transaction cap €500 000 · dual-use review €100 000+")
    print(f"  Storage:  {db_path}")
    print()

    def _policy(inputs: dict[str, Any]) -> tuple[bool, str | None]:
        req = inputs.get("request", {})
        amount = int(req.get("amount", 0))
        dual_use = bool(req.get("dual_use", False))
        if amount > 500_000:
            return False, "export_control_hard_cap"
        if dual_use and amount > 100_000:
            return False, "dual_use_review_required"
        return True, None

    sentinel = Sentinel(
        storage=SQLiteStorage(str(db_path)),
        project="sentinel-demo",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator(
            {"policies/export_control.py": _policy}
        ),
    )

    @sentinel.trace(policy="policies/export_control.py")
    def approve(request: dict[str, Any]) -> dict[str, Any]:
        return {"decision": "approved", "amount": request["amount"]}

    # Step 1 — 10 realistic, named decisions
    print(f"[1/5] Running {len(_DEMO_SCENARIOS)} realistic decisions...")
    allow = deny = 0
    total_blocked_value = 0
    for idx, (label, amount, dual_use) in enumerate(_DEMO_SCENARIOS, start=1):
        request = {
            "amount": amount,
            "dual_use": dual_use,
            "requester": f"agent-{idx:02d}",
        }
        try:
            approve(request=request)
            allow += 1
            mark = "ALLOW"
            detail = ""
        except PolicyDeniedError as exc:
            deny += 1
            total_blocked_value += amount
            mark = "BLOCKED"
            detail = f"rule={_extract_policy_rule(str(exc))}"
        label_col = f"{label:<46}"
        amount_col = f"€{amount:>9,}"
        if mark == "BLOCKED":
            print(f"  [{idx:02d}/10] {label_col} {amount_col}  {mark}")
            print(f"         └─ {detail}   (halted before execution, audit trail recorded)")
        else:
            print(f"  [{idx:02d}/10] {label_col} {amount_col}  {mark}")
    print(f"      ALLOW: {allow} · BLOCKED: {deny}")
    print()

    # Step 2 — Kill switch (Art. 14 human oversight)
    if not args.no_kill_switch:
        print("[2/5] Engaging kill switch (EU AI Act Art. 14)...")
        sentinel.engage_kill_switch("compliance review in progress")
        blocked = 0
        for i in range(3):
            try:
                approve(request={"amount": 1_000, "dual_use": False,
                                 "requester": f"halted-{i}"})
            except Exception:
                blocked += 1
        print(f"      Blocked {blocked} further requests while engaged")
        sentinel.disengage_kill_switch("review complete")
        print("      Kill switch disengaged — decisions resume")
        print()
    else:
        print("[2/5] (kill-switch demo skipped via --no-kill-switch)")
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
    # never seen Sentinel before. The BLOCKED line carries the story.
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
    print(_row(
        f"{total_decisions} decisions traced",
        f"({allow} ALLOW · {deny} BLOCKED, EU-sovereign storage)",
    ))
    print(ks_row)
    print(_row("Sovereignty scan", f"({score_pct}% score)"))
    print(_row(
        "EU AI Act compliance check",
        f"({compliance.overall} — {compliance.days_to_enforcement} days remaining)",
    ))
    print(_row("Privacy", "inputs/outputs stored as SHA-256 hashes"))
    print(_row("HTML report generated", ""))
    print()
    print("  What just happened")
    print("  ──────────────────")
    if deny > 0:
        print(
            f"  The AI agent wanted to approve €{total_blocked_value:,} of "
            "dual-use / above-cap exports."
        )
        print(
            f"  Sentinel halted {deny} transaction{'s' if deny != 1 else ''} "
            "pending human review."
        )
    else:
        print(
            "  Every request passed policy this run — but the trail still "
            "records agent, policy, input hash, and result for each one."
        )
    print(
        "  Every decision — ALLOW or BLOCKED — is in the immutable audit trail."
    )
    print()
    print(f"  Report saved: {out_path}")
    print(f"  Open it:      {_open_hint(out_path)}")
    print()
    print("  Next steps:   sentinel audit-gap")
    print("                sentinel attestation generate")
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


def _extract_policy_rule(exception_message: str) -> str:
    """Pick the triggering rule name out of a PolicyDeniedError message.

    Falls back to a readable sentinel when the message does not follow
    the canonical ``... Rule: <name>. Trace ID: ...`` shape, so the demo
    always prints *something* meaningful on the BLOCKED line.
    """
    if "Rule:" in exception_message:
        return exception_message.split("Rule:")[1].split(".")[0].strip()
    return "policy_denied"


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
                _print_open_hint(args.output)
            else:
                print(unified._render_html())
        elif args.json:
            content = json.dumps(unified.as_dict(), indent=2, default=str)
            if args.output:
                Path(args.output).write_text(content, encoding="utf-8")
                print(f"Wrote {args.output}")
                _print_open_hint(args.output)
            else:
                print(content)
        else:
            content = unified.as_text()
            if args.output:
                Path(args.output).write_text(content, encoding="utf-8")
                print(f"Wrote {args.output}")
                _print_open_hint(args.output)
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
        _print_open_hint(args.output)
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
        _print_open_hint(args.output)
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
    _print_open_hint(args.output)
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


def _cmd_ci_check(args: argparse.Namespace) -> int:
    from sentinel.ci import run_ci_checks

    sentinel = _make_default_sentinel()

    manifesto_instance = None
    if args.manifesto:
        cls = _load_manifesto(args.manifesto)
        if cls is None:
            print(
                f"Could not resolve manifesto: {args.manifesto}",
                file=sys.stderr,
            )
            return 2
        manifesto_instance = cls()

    result = run_ci_checks(
        sentinel=sentinel,
        manifesto=manifesto_instance,
        repo_root=args.repo,
    )
    if args.json:
        print(result.as_json())
    else:
        print(result.as_text())
    return result.exit_code


def _resolve_evidence_pack_db(explicit: str | None) -> str:
    """
    Pick which SQLite path ``sentinel evidence-pack`` should read from.

    Priority:
      1. Explicit ``--db`` flag (honoured verbatim).
      2. The pilot database at ``./.sentinel/traces.db`` if it exists
         — so the golden path `quickstart → run → evidence-pack` just
         works without the user having to pass flags.
      3. In-memory fallback (empty pack) — preserves legacy behaviour
         for callers who invoke evidence-pack as a smoke check.
    """
    if explicit is not None:
        return explicit

    from sentinel.pilot.config import default_pilot_paths

    _, _, pilot_db = default_pilot_paths()
    if pilot_db.exists():
        return str(pilot_db)

    return ":memory:"


def _resolve_evidence_pack_output(explicit: str | None) -> Path:
    """Default the evidence pack output path to ./audit.pdf in cwd."""
    if explicit is not None:
        return Path(explicit)
    return Path.cwd() / "audit.pdf"


def _cmd_evidence_pack(args: argparse.Namespace) -> int:
    from sentinel.compliance.evidence_pack import (
        EvidencePackOptions,
        render_evidence_pdf,
    )

    def _parse_iso(value: str | None, label: str) -> Any:
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            print(
                f"evidence-pack: --{label} is not a valid ISO 8601 "
                f"datetime: {value}",
                file=sys.stderr,
            )
            return _PARSE_ERROR

    since = _parse_iso(args.since, "since")
    if since is _PARSE_ERROR:
        return 2
    until = _parse_iso(args.until, "until")
    if until is _PARSE_ERROR:
        return 2

    storage = SQLiteStorage(_resolve_evidence_pack_db(args.db))
    sentinel = Sentinel(
        storage=storage,
        project=args.project or "sentinel-cli",
        data_residency=DataResidency.LOCAL,
    )

    manifesto_instance = None
    if args.manifesto:
        cls = _load_manifesto(args.manifesto)
        if cls is None:
            print(
                f"Could not resolve manifesto: {args.manifesto}",
                file=sys.stderr,
            )
            return 2
        manifesto_instance = cls()

    options = EvidencePackOptions(
        since=since,
        until=until,
        project=args.project,
        financial_sector=args.financial_sector,
        critical_infrastructure=args.critical_infrastructure,
        max_traces=args.max_traces,
        title=args.title,
    )
    output_path = _resolve_evidence_pack_output(args.output)
    try:
        path = render_evidence_pdf(
            sentinel=sentinel,
            options=options,
            output=str(output_path),
            manifesto=manifesto_instance,
        )
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"Wrote {path}")
    _print_open_hint(path)
    print()
    print("  next    sentinel audit-gap     # see what else your auditor will ask for")
    return 0


_PARSE_ERROR = object()


def _cmd_comply_sign(args: argparse.Namespace) -> int:
    """PAdES-sign a PDF using the default self-signed cert."""
    from sentinel import comply

    src = Path(args.input).expanduser()
    if not src.exists():
        print(f"comply sign: {src} not found", file=sys.stderr)
        return 2

    output = Path(args.output).expanduser() if args.output else None
    try:
        signed = comply.sign(src, output, reason=args.reason)
    except RuntimeError as exc:  # pragma: no cover - only hit when extra missing
        print(f"comply sign: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote signed PDF: {signed}")
    _print_open_hint(signed)
    return 0


def _cmd_comply_verify(args: argparse.Namespace) -> int:
    """Verify PAdES signatures on a PDF."""
    from sentinel import comply

    src = Path(args.input).expanduser()
    if not src.exists():
        print(f"comply verify: {src} not found", file=sys.stderr)
        return 2

    try:
        result = comply.verify(src)
    except RuntimeError as exc:  # pragma: no cover - only hit when extra missing
        print(f"comply verify: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "✓ valid" if result.valid else "✗ invalid"
        print(f"{status}: {result.detail}")

    return 0 if result.valid else 1


def _cmd_chain_verify(args: argparse.Namespace) -> int:
    """Verify a chain of attestations read from a JSON file."""
    from sentinel.chain import verify_chain

    try:
        raw = Path(args.input).expanduser().read_text(encoding="utf-8")
        attestations = json.loads(raw)
    except FileNotFoundError:
        print(f"chain verify: {args.input} not found", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"chain verify: invalid JSON — {exc}", file=sys.stderr)
        return 2

    if not isinstance(attestations, list):
        print(
            "chain verify: input must be a JSON list of attestations",
            file=sys.stderr,
        )
        return 2

    result = verify_chain(attestations)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        status = "✓ verified" if result.verified else "✗ failed"
        print(f"{status}: {result.detail}")
        print(f"steps checked: {result.steps_checked}")
        if result.first_failure_index is not None:
            print(f"first failure at index: {result.first_failure_index}")

    return 0 if result.verified else 1


def _cmd_key_init(args: argparse.Namespace) -> int:
    """Create the default Ed25519 attestation key if it does not exist."""
    try:
        from sentinel.crypto.ed25519_signer import (
            Ed25519Signer,
            _default_key_path,
        )
    except ImportError as exc:  # pragma: no cover - only hit when extra missing
        print(str(exc), file=sys.stderr)
        return 2

    path = Path(args.path).expanduser() if args.path else _default_key_path()

    if path.exists() and not args.force:
        print(f"key already exists at {path}", file=sys.stderr)
        print("pass --force to overwrite", file=sys.stderr)
        return 1

    try:
        signer = Ed25519Signer.generate()
        signer.save(path)
    except ImportError as exc:  # pragma: no cover - only hit when extra missing
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Wrote Ed25519 private key: {path} (mode 0o600)")
    print("This key signs every decision attestation by default.")
    print("Public key (share freely with verifiers):")
    print(signer.public_key_pem().decode("ascii").rstrip())
    return 0


def _cmd_key_path(args: argparse.Namespace) -> int:
    """Print the resolved default Ed25519 key path."""
    _ = args
    from sentinel.crypto.ed25519_signer import _default_key_path

    print(str(_default_key_path()))
    return 0


def _cmd_key_public(args: argparse.Namespace) -> int:
    """Print the PEM-encoded Ed25519 public key."""
    try:
        from sentinel.crypto.ed25519_signer import (
            Ed25519Signer,
            _default_key_path,
        )
    except ImportError as exc:  # pragma: no cover - only hit when extra missing
        print(str(exc), file=sys.stderr)
        return 2

    path = Path(args.path).expanduser() if args.path else _default_key_path()
    if not path.exists():
        print(f"no Ed25519 key at {path}", file=sys.stderr)
        print("run `sentinel key init` to create one", file=sys.stderr)
        return 1

    try:
        signer = Ed25519Signer.from_path(path)
    except (ImportError, ValueError) as exc:  # pragma: no branch
        # ImportError only fires when the cryptography extra is
        # missing (covered by a dedicated install-path check, not a
        # unit test). ValueError is covered by the non-Ed25519-key
        # test. The branch discrimination is irrelevant to coverage.
        print(str(exc), file=sys.stderr)
        return 2

    print(signer.public_key_pem().decode("ascii").rstrip())
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
        _print_open_hint(args.output)
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
# Self-serve pilot commands
# ---------------------------------------------------------------------------


def _cmd_quickstart(args: argparse.Namespace) -> int:
    from sentinel.pilot.quickstart import run_quickstart
    from sentinel.pilot.render import render_quickstart_text

    result = run_quickstart(force=args.force)
    sys.stdout.write(render_quickstart_text(result))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    from sentinel import __version__
    from sentinel.pilot.render import render_status_text
    from sentinel.pilot.status import compute_pilot_status

    try:
        status = compute_pilot_status(version=__version__)
    except ValueError as exc:
        print(f"status: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(status.to_dict(), indent=2, sort_keys=True))
        return 0

    sys.stdout.write(render_status_text(status))
    return 0


def _cmd_audit_gap(args: argparse.Namespace) -> int:
    from sentinel.pilot.audit_gap import compute_audit_gap
    from sentinel.pilot.config import default_pilot_paths, load_pilot_config
    from sentinel.pilot.render import render_audit_gap_text

    _, config_path, db_path = default_pilot_paths()

    try:
        cfg = load_pilot_config(config_path)
    except ValueError as exc:
        print(f"audit-gap: {exc}", file=sys.stderr)
        return 2

    trace_count = _count_traces_at(db_path)
    storage_path = (
        cfg.storage_path if cfg is not None else str(db_path)
    )

    report = compute_audit_gap(
        config=cfg,
        trace_count=trace_count,
        storage_path=storage_path,
        profile=args.profile,
    )

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0

    sys.stdout.write(render_audit_gap_text(report))
    return 0


def _cmd_fix_kill_switch(args: argparse.Namespace) -> int:
    from sentinel.pilot.fixes import fix_kill_switch
    from sentinel.pilot.render import render_fix_text

    result = fix_kill_switch()
    if args.json:
        print(
            json.dumps(
                {
                    "fix_id": result.fix_id,
                    "succeeded": result.succeeded,
                    "points_delta": result.points_delta,
                    "detail": result.detail,
                    "artefact_path": str(result.artefact_path)
                    if result.artefact_path
                    else None,
                    "config_path": str(result.config_path)
                    if result.config_path
                    else None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if result.succeeded else 1

    sys.stdout.write(render_fix_text(result))
    return 0 if result.succeeded else 1


def _cmd_fix_retention(args: argparse.Namespace) -> int:
    from sentinel.pilot.fixes import fix_retention
    from sentinel.pilot.render import render_fix_text

    result = fix_retention(days=args.days)
    if args.json:
        print(
            json.dumps(
                {
                    "fix_id": result.fix_id,
                    "succeeded": result.succeeded,
                    "points_delta": result.points_delta,
                    "detail": result.detail,
                    "config_path": str(result.config_path)
                    if result.config_path
                    else None,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if result.succeeded else 1

    sys.stdout.write(render_fix_text(result))
    return 0 if result.succeeded else 1


def _count_traces_at(db_path: Path) -> int:
    """
    Cheap, safe trace count for audit-gap.

    Uses a read-only SQLite connection so we never accidentally
    create the database as a side effect of running audit-gap on a
    fresh directory. Returns 0 on any error — a missing/empty DB is
    indistinguishable from "no traces yet," which is what audit-gap
    wants to see.
    """
    if not db_path.exists():
        return 0
    try:
        import sqlite3

        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM decision_traces"
            ).fetchone()
            return int(row[0]) if row else 0
    except Exception:  # pragma: no cover - defensive only
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
