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
    assert "dashboard" in out
    assert "manifesto" in out


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
