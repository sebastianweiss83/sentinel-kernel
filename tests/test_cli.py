"""
tests/test_cli.py
~~~~~~~~~~~~~~~~~
Covers every subcommand branch in sentinel.cli.

No network. No real OPA binary. Uses tmp_path for file outputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel import cli

# ---------------------------------------------------------------------------
# Top-level / help paths
# ---------------------------------------------------------------------------


def test_no_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main([])
    assert rc == 1
    out = capsys.readouterr().out
    assert "usage" in out.lower()
    assert "scan" in out
    assert "compliance" in out
    assert "report" in out


# ---------------------------------------------------------------------------
# sentinel demo
# ---------------------------------------------------------------------------


def test_demo_runs_end_to_end(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_path = tmp_path / "demo_report.html"
    rc = cli.main(["demo", "--output", str(out_path), "--no-kill-switch"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SENTINEL DEMO" in out
    assert "Defence logistics" in out
    assert "10 realistic decisions" in out
    assert "BLOCKED" in out  # at least one narrative blocked moment
    assert "EU AI Act compliance checker" in out
    assert "HTML sovereignty report" in out
    assert "Report saved" in out
    assert out_path.exists()
    content = out_path.read_text()
    assert content.startswith("<!doctype html>")
    assert "Sentinel Evidence Report" in content


def test_demo_output_surfaces_narrative_payoff(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The demo's 'what just happened' block is the pitch moment — it
    must surface the total blocked value and the BLOCKED count so a
    first-time reader sees the story, not just a log."""
    out_path = tmp_path / "demo_report.html"
    rc = cli.main(["demo", "--output", str(out_path), "--no-kill-switch"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "What just happened" in out
    assert "€1,260,000" in out  # sum of three blocked scenarios
    assert "3 transactions" in out
    assert "immutable audit trail" in out


def test_demo_with_kill_switch(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_path = tmp_path / "demo_report.html"
    rc = cli.main(["demo", "--output", str(out_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "kill switch" in out.lower()
    assert "engaging kill switch" in out.lower() or "engaged" in out.lower()
    assert out_path.exists()


def test_demo_default_output_lands_in_cwd(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Without --output, `sentinel demo` must write the report to the
    current working directory and print an `open 'PATH'` command that
    names the exact same path. This is the regression guard for the
    v3.0.2 UX bug where the open command pointed at a different file.
    """
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["demo", "--no-kill-switch"])
    assert rc == 0

    # File must be physically present in the CWD
    expected = (tmp_path / "sentinel_demo_report.html").resolve()
    assert expected.exists()

    out = capsys.readouterr().out

    # The "Report saved" line and the "open" line must name the SAME path
    assert f"Report saved: {expected}" in out
    assert f"open '{expected}'" in out


def test_demo_falls_back_to_tempdir_when_cwd_not_writable(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    If the CWD is not writable (read-only mount, unusual sandbox), the
    demo must not crash. It must write into tempdir and say so clearly.
    """
    monkeypatch.chdir(tmp_path)

    import os as _os

    real_access = _os.access

    def fake_access(path: object, mode: int) -> bool:
        # Deny write to the current CWD only
        try:
            if Path(str(path)).resolve() == tmp_path.resolve() and mode & _os.W_OK:
                return False
        except Exception:
            pass
        return real_access(path, mode)

    monkeypatch.setattr(_os, "access", fake_access)

    rc = cli.main(["demo", "--no-kill-switch"])
    assert rc == 0

    # File must NOT be in CWD
    assert not (tmp_path / "sentinel_demo_report.html").exists()

    out = capsys.readouterr().out
    assert "CWD not writable" in out
    # Open line must still quote an absolute path
    assert "open '" in out


def test_extract_policy_rule_canonical_shape() -> None:
    """Standard PolicyDeniedError message yields the rule name."""
    msg = (
        "Policy 'policies/export.py' denied the action. "
        "Rule: dual_use_review_required. "
        "Trace ID: 01hx7k"
    )
    assert cli._extract_policy_rule(msg) == "dual_use_review_required"


def test_extract_policy_rule_unknown_shape_falls_back() -> None:
    """Unexpected message shape falls back to 'policy_denied'."""
    assert cli._extract_policy_rule("some garbled thing") == "policy_denied"
    assert cli._extract_policy_rule("") == "policy_denied"


def test_demo_all_allow_path_still_prints_summary(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the scenarios produced zero BLOCKED decisions, the 'What just
    happened' block still renders — the trail-is-still-recorded message
    is the correct framing. Exercised by patching the demo scenarios to
    an all-under-cap set."""
    monkeypatch.setattr(
        cli,
        "_DEMO_SCENARIOS",
        (
            ("Low-value routine A", 1_000, False),
            ("Low-value routine B", 2_000, False),
        ),
    )
    rc = cli.main(["demo", "--output", str(tmp_path / "r.html"), "--no-kill-switch"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "What just happened" in out
    assert "Every request passed policy" in out
    assert "immutable audit trail" in out


def test_resolve_demo_output_honours_explicit_path(tmp_path: Path) -> None:
    explicit = tmp_path / "custom.html"
    resolved, reason = cli._resolve_demo_output(str(explicit))
    assert resolved == explicit.resolve()
    assert reason is None


def test_resolve_demo_output_defaults_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    resolved, reason = cli._resolve_demo_output(None)
    assert resolved == (tmp_path / "sentinel_demo_report.html").resolve()
    assert reason is None


def test_compliance_without_subcommand_prints_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli.main(["compliance"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "compliance" in out.lower()


def test_manifesto_without_subcommand_prints_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli.main(["manifesto"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "manifesto" in out.lower()


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


def test_scan_default_runs_all_layers(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["scan"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "RUNTIME" in out
    assert "CI/CD" in out
    assert "INFRA" in out


def test_scan_runtime_only(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["scan", "--runtime"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "RUNTIME" in out
    assert "CI/CD" not in out
    assert "INFRA" not in out


def test_scan_cicd_only(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: CI\n")
    rc = cli.main(["scan", "--cicd", "--repo", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "CI/CD" in out
    assert "RUNTIME" not in out


def test_scan_infra_only(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('provider "aws" {}\n')
    rc = cli.main(["scan", "--infra", "--repo", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "INFRA" in out


def test_scan_all_flag_equivalent_to_default(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli.main(["scan", "--all"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "RUNTIME" in out
    assert "CI/CD" in out
    assert "INFRA" in out


def test_scan_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["scan", "--runtime", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "runtime" in data
    assert "total_packages" in data["runtime"]


# ---------------------------------------------------------------------------
# compliance check
# ---------------------------------------------------------------------------


def test_compliance_check_text(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["compliance", "check"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Art." in out


def test_compliance_check_html(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["compliance", "check", "--html"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "<html" in out.lower() or "<!doctype" in out.lower()


def test_compliance_check_json(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["compliance", "check", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, dict)


def test_compliance_check_output_to_file(tmp_path: Path) -> None:
    out_file = tmp_path / "compliance.html"
    rc = cli.main(["compliance", "check", "--html", "--output", str(out_file)])
    assert rc == 0
    assert out_file.exists()
    assert out_file.stat().st_size > 100


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def test_report_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["report"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "<html" in out.lower() or "<!doctype" in out.lower()


def test_report_to_file(tmp_path: Path) -> None:
    out_file = tmp_path / "report.html"
    rc = cli.main(["report", "--output", str(out_file)])
    assert rc == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "<html" in content.lower() or "<!doctype" in content.lower()


def test_report_with_manifesto_file(tmp_path: Path) -> None:
    manifest = tmp_path / "my_manifest.py"
    manifest.write_text(
        """
from sentinel.manifesto import SentinelManifesto, EUOnly

class MyManifest(SentinelManifesto):
    jurisdiction = EUOnly()
"""
    )
    out_file = tmp_path / "report.html"
    rc = cli.main(
        [
            "report",
            "--manifesto",
            f"{manifest}:MyManifest",
            "--output",
            str(out_file),
            "--repo",
            str(tmp_path),
        ]
    )
    assert rc == 0
    assert out_file.exists()


# ---------------------------------------------------------------------------
# dashboard
# ---------------------------------------------------------------------------


def test_dashboard_single_frame(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["dashboard", "--frames", "1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SENTINEL" in out
    assert "Sovereignty score" in out


def test_dashboard_multi_frame(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["dashboard", "--frames", "2", "--interval", "0.01"])
    assert rc == 0


# ---------------------------------------------------------------------------
# manifesto check
# ---------------------------------------------------------------------------


def test_manifesto_check_from_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "m.py"
    manifest.write_text(
        """
from sentinel.manifesto import SentinelManifesto, EUOnly

class Demo(SentinelManifesto):
    jurisdiction = EUOnly()
"""
    )
    rc = cli.main(
        ["manifesto", "check", f"{manifest}:Demo", "--repo", str(tmp_path)]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "MANIFESTO REPORT" in out


def test_manifesto_check_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "m.py"
    manifest.write_text(
        """
from sentinel.manifesto import SentinelManifesto, EUOnly

class Demo(SentinelManifesto):
    jurisdiction = EUOnly()
"""
    )
    rc = cli.main(
        [
            "manifesto",
            "check",
            f"{manifest}:Demo",
            "--json",
            "--repo",
            str(tmp_path),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "overall_score" in data


def test_manifesto_check_unresolvable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli.main(["manifesto", "check", "no_colon_in_ref"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "Could not resolve" in err


def test_manifesto_check_missing_class(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "m.py"
    manifest.write_text("x = 1\n")
    rc = cli.main(["manifesto", "check", f"{manifest}:DoesNotExist"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "Could not resolve" in err


def test_manifesto_check_not_a_subclass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = tmp_path / "m.py"
    manifest.write_text("class NotAManifesto:\n    pass\n")
    rc = cli.main(["manifesto", "check", f"{manifest}:NotAManifesto"])
    assert rc == 2


def test_load_manifesto_from_dotted_module() -> None:
    cls = cli._load_manifesto("sentinel.manifesto:SentinelManifesto")
    assert cls is not None
    assert cls.__name__ == "SentinelManifesto"


def test_load_manifesto_bad_spec_returns_none(tmp_path: Path) -> None:
    # File does not exist
    missing = tmp_path / "missing.py"
    assert cli._load_manifesto(f"{missing}:Anything") is None


def test_dunder_main_module_delegates_to_cli_main() -> None:
    import sentinel.__main__ as dunder_main

    assert dunder_main.main is cli.main


def test_python_dash_m_sentinel_help_exits_zero() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "sentinel", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "sentinel" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Cross-platform "Open it:" hint — helper + every file-writing command
# ---------------------------------------------------------------------------


def test_open_hint_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    """On darwin the hint uses ``open '<path>'``."""
    import sys as _sys

    monkeypatch.setattr(_sys, "platform", "darwin")
    assert cli._open_hint("/tmp/x.html") == "open '/tmp/x.html'"


def test_open_hint_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """On win32 the hint uses ``start "" "<path>"``."""
    import sys as _sys

    monkeypatch.setattr(_sys, "platform", "win32")
    assert cli._open_hint(r"C:\tmp\x.html") == 'start "" "C:\\tmp\\x.html"'


def test_open_hint_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """On every other platform the hint uses ``xdg-open '<path>'``."""
    import sys as _sys

    monkeypatch.setattr(_sys, "platform", "linux")
    assert cli._open_hint("/tmp/x.html") == "xdg-open '/tmp/x.html'"


def test_print_open_hint_emits_indented_arrow_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``_print_open_hint`` produces an indented ``→`` line a user can copy."""
    cli._print_open_hint("/tmp/out.pdf")
    out = capsys.readouterr().out
    # Indented two spaces, arrow marker, then the platform-appropriate command
    assert out.startswith("  → ")
    assert "/tmp/out.pdf" in out
    assert "\n" in out


def test_report_to_file_prints_open_hint(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """``sentinel report --output`` must print the Open-it hint after Wrote."""
    out_file = tmp_path / "sov.html"
    rc = cli.main(["report", "--output", str(out_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert f"Wrote {out_file}" in out
    assert f"  → {cli._open_hint(str(out_file))}" in out


def test_compliance_check_html_to_file_prints_hint(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_file = tmp_path / "compliance.html"
    rc = cli.main(["compliance", "check", "--html", "--output", str(out_file)])
    assert rc == 0
    text = capsys.readouterr().out
    assert f"Wrote {out_file}" in text
    assert f"  → {cli._open_hint(str(out_file))}" in text


def test_compliance_check_json_to_file_prints_hint(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_file = tmp_path / "compliance.json"
    rc = cli.main(["compliance", "check", "--json", "--output", str(out_file)])
    assert rc == 0
    text = capsys.readouterr().out
    assert f"Wrote {out_file}" in text
    assert f"  → {cli._open_hint(str(out_file))}" in text


def test_compliance_check_text_to_file_prints_hint(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_file = tmp_path / "compliance.txt"
    rc = cli.main(["compliance", "check", "--output", str(out_file)])
    assert rc == 0
    text = capsys.readouterr().out
    assert f"Wrote {out_file}" in text
    assert f"  → {cli._open_hint(str(out_file))}" in text


def test_compliance_check_unified_html_to_file_prints_hint(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_file = tmp_path / "unified.html"
    rc = cli.main(
        [
            "compliance",
            "check",
            "--all-frameworks",
            "--html",
            "--output",
            str(out_file),
        ]
    )
    assert rc == 0
    text = capsys.readouterr().out
    assert f"Wrote {out_file}" in text
    assert f"  → {cli._open_hint(str(out_file))}" in text


def test_compliance_check_unified_json_to_file_prints_hint(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_file = tmp_path / "unified.json"
    rc = cli.main(
        [
            "compliance",
            "check",
            "--financial-sector",
            "--json",
            "--output",
            str(out_file),
        ]
    )
    assert rc == 0
    text = capsys.readouterr().out
    assert f"Wrote {out_file}" in text
    assert f"  → {cli._open_hint(str(out_file))}" in text


def test_compliance_check_unified_text_to_file_prints_hint(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_file = tmp_path / "unified.txt"
    rc = cli.main(
        [
            "compliance",
            "check",
            "--critical-infrastructure",
            "--output",
            str(out_file),
        ]
    )
    assert rc == 0
    text = capsys.readouterr().out
    assert f"Wrote {out_file}" in text
    assert f"  → {cli._open_hint(str(out_file))}" in text


def test_attestation_generate_to_file_prints_hint(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_file = tmp_path / "att.json"
    rc = cli.main(["attestation", "generate", "--output", str(out_file)])
    assert rc == 0
    text = capsys.readouterr().out
    assert f"Wrote {out_file}" in text
    assert f"  → {cli._open_hint(str(out_file))}" in text
