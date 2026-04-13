"""
tests/test_cli_ci_check.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Covers ``sentinel.ci.checks`` and the ``sentinel ci-check`` CLI.

No network. Injects a fake RuntimeScanner for the failure branches so
the tests remain fully deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel import Sentinel, cli
from sentinel.ci import CICheckOutcome, CICheckResult, run_ci_checks
from sentinel.ci.checks import FAIL, PASS, SKIP
from sentinel.scanner.runtime import PackageReport, RuntimeScanner, ScanResult
from sentinel.storage import SQLiteStorage

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_sentinel() -> Sentinel:
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="test-ci",
    )


class _StubScanner:
    """A RuntimeScanner-compatible stub that returns a canned ScanResult."""

    def __init__(self, result: ScanResult) -> None:
        self._result = result

    def scan(self) -> ScanResult:
        return self._result


def _clean_scan() -> ScanResult:
    return ScanResult(
        packages=[
            PackageReport(
                name="pytest",
                version="8.0",
                parent_company="Pytest-dev",
                jurisdiction="EU",
                cloud_act_exposure=False,
                in_critical_path=False,
                is_optional=False,
            )
        ],
        critical_path_violations=[],
    )


def _dirty_scan() -> ScanResult:
    return ScanResult(
        packages=[
            PackageReport(
                name="boto3",
                version="1.0",
                parent_company="Amazon",
                jurisdiction="US",
                cloud_act_exposure=True,
                in_critical_path=True,
                is_optional=False,
            )
        ],
        critical_path_violations=["boto3 (Amazon, US)"],
    )


# ---------------------------------------------------------------------------
# CICheckResult behaviour
# ---------------------------------------------------------------------------


def test_result_overall_pass_when_all_pass() -> None:
    r = CICheckResult(
        outcomes=[
            CICheckOutcome(name="a", status=PASS, summary="ok"),
            CICheckOutcome(name="b", status=PASS, summary="ok"),
        ]
    )
    assert r.overall == "PASS"
    assert r.exit_code == 0


def test_result_overall_partial_when_skip_present() -> None:
    r = CICheckResult(
        outcomes=[
            CICheckOutcome(name="a", status=PASS, summary="ok"),
            CICheckOutcome(name="b", status=SKIP, summary="skipped"),
        ]
    )
    assert r.overall == "PARTIAL"
    assert r.exit_code == 0


def test_result_overall_fail_when_any_fail() -> None:
    r = CICheckResult(
        outcomes=[
            CICheckOutcome(name="a", status=PASS, summary="ok"),
            CICheckOutcome(name="b", status=FAIL, summary="bad", detail="x\ny"),
        ]
    )
    assert r.overall == "FAIL"
    assert r.exit_code == 1


def test_result_as_text_includes_detail_lines() -> None:
    r = CICheckResult(
        outcomes=[
            CICheckOutcome(name="a", status=FAIL, summary="bad", detail="x\ny"),
        ]
    )
    text = r.as_text()
    assert "SENTINEL CI CHECK" in text
    assert "[FAIL] a" in text
    assert "x" in text and "y" in text
    assert "Overall: FAIL" in text


def test_result_as_json_roundtrip() -> None:
    r = CICheckResult(
        outcomes=[CICheckOutcome(name="a", status=PASS, summary="ok")]
    )
    data = json.loads(r.as_json())
    assert data["overall"] == "PASS"
    assert data["exit_code"] == 0
    assert data["outcomes"][0]["name"] == "a"
    assert r.as_dict()["outcomes"][0]["status"] == "PASS"


# ---------------------------------------------------------------------------
# run_ci_checks — wrapping existing APIs
# ---------------------------------------------------------------------------


def test_run_ci_checks_clean_environment() -> None:
    result = run_ci_checks(
        sentinel=_make_sentinel(),
        scanner=_StubScanner(_clean_scan()),
    )
    # eu_ai_act + sovereignty_scan + manifesto(SKIP)
    names = [o.name for o in result.outcomes]
    assert names == ["eu_ai_act", "sovereignty_scan", "manifesto"]
    sov = next(o for o in result.outcomes if o.name == "sovereignty_scan")
    assert sov.status == "PASS"
    man = next(o for o in result.outcomes if o.name == "manifesto")
    assert man.status == "SKIP"
    # Overall with a SKIP is PARTIAL but still exit 0
    assert result.overall == "PARTIAL"
    assert result.exit_code == 0


def test_run_ci_checks_sovereignty_violation() -> None:
    result = run_ci_checks(
        sentinel=_make_sentinel(),
        scanner=_StubScanner(_dirty_scan()),
    )
    sov = next(o for o in result.outcomes if o.name == "sovereignty_scan")
    assert sov.status == "FAIL"
    assert "boto3" in sov.detail
    assert result.overall == "FAIL"
    assert result.exit_code == 1


def test_run_ci_checks_with_passing_manifesto() -> None:
    from sentinel.manifesto import (
        AcknowledgedGap,
        EUOnly,
        OnPremiseOnly,
        Required,
        SentinelManifesto,
        ZeroExposure,
    )

    class _PassingManifesto(SentinelManifesto):
        jurisdiction = EUOnly()
        kill_switch = Required()
        airgap = Required()
        cloud_act = ZeroExposure()
        storage = OnPremiseOnly(country="EU")
        ci_cd = AcknowledgedGap(
            provider="GitHub (Microsoft)",
            migrating_to="Self-hosted Forgejo",
            by="2027-Q2",
            reason="no production-ready EU alternative yet",
        )

    result = run_ci_checks(
        sentinel=_make_sentinel(),
        scanner=_StubScanner(_clean_scan()),
        manifesto=_PassingManifesto(),
    )
    man = next(o for o in result.outcomes if o.name == "manifesto")
    assert man.status == "PASS"
    assert "no hard gaps" in man.summary


def test_run_ci_checks_with_failing_manifesto() -> None:
    from datetime import datetime

    from sentinel.manifesto.base import (
        Gap,
        ManifestoReport,
        SentinelManifesto,
    )

    class _FailingManifesto(SentinelManifesto):
        def check(self, *, sentinel=None, repo_root=".") -> ManifestoReport:
            return ManifestoReport(
                timestamp=datetime.now(),
                overall_score=0.5,
                gaps=[
                    Gap(
                        dimension="cloud_act",
                        expected="no exposure",
                        actual="exposed",
                        severity="critical",
                    ),
                ],
            )

    result = run_ci_checks(
        sentinel=_make_sentinel(),
        scanner=_StubScanner(_clean_scan()),
        manifesto=_FailingManifesto(),
    )
    man = next(o for o in result.outcomes if o.name == "manifesto")
    assert man.status == "FAIL"
    assert "cloud_act" in man.detail
    assert result.exit_code == 1


def test_run_ci_checks_default_scanner_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover the branch where no scanner is injected — constructs a real one."""

    def _fake_scan(self: RuntimeScanner) -> ScanResult:
        return _clean_scan()

    monkeypatch.setattr(RuntimeScanner, "scan", _fake_scan)
    result = run_ci_checks(sentinel=_make_sentinel())
    assert any(o.name == "sovereignty_scan" for o in result.outcomes)


def test_run_ci_checks_eu_checker_injection() -> None:
    """Cover the eu_checker injection branch."""
    from sentinel.compliance.euaiact import EUAIActChecker

    result = run_ci_checks(
        sentinel=_make_sentinel(),
        scanner=_StubScanner(_clean_scan()),
        eu_checker=EUAIActChecker(),
    )
    eu = next(o for o in result.outcomes if o.name == "eu_ai_act")
    assert eu.status == "PASS"


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_ci_check_text(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(RuntimeScanner, "scan", lambda self: _clean_scan())
    rc = cli.main(["ci-check"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "SENTINEL CI CHECK" in out
    assert "eu_ai_act" in out
    assert "sovereignty_scan" in out
    assert "manifesto" in out


def test_cli_ci_check_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(RuntimeScanner, "scan", lambda self: _clean_scan())
    rc = cli.main(["ci-check", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["overall"] in ("PASS", "PARTIAL")
    assert {o["name"] for o in data["outcomes"]} == {
        "eu_ai_act",
        "sovereignty_scan",
        "manifesto",
    }


def test_cli_ci_check_with_manifesto_file(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(RuntimeScanner, "scan", lambda self: _clean_scan())
    manifesto_file = tmp_path / "my_manifesto.py"
    manifesto_file.write_text(
        "from sentinel.manifesto import (\n"
        "    AcknowledgedGap, EUOnly, OnPremiseOnly, Required,\n"
        "    SentinelManifesto, ZeroExposure,\n"
        ")\n"
        "class MyManifesto(SentinelManifesto):\n"
        "    jurisdiction = EUOnly()\n"
        "    kill_switch = Required()\n"
        "    airgap = Required()\n"
        "    cloud_act = ZeroExposure()\n"
        "    storage = OnPremiseOnly(country='EU')\n"
        "    ci_cd = AcknowledgedGap(\n"
        "        provider='GitHub (Microsoft)',\n"
        "        migrating_to='Self-hosted Forgejo',\n"
        "        by='2027-Q2',\n"
        "        reason='no EU alternative yet',\n"
        "    )\n",
        encoding="utf-8",
    )
    rc = cli.main(
        [
            "ci-check",
            "--manifesto",
            f"{manifesto_file}:MyManifesto",
            "--repo",
            str(tmp_path),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "manifesto" in out


def test_cli_ci_check_invalid_manifesto_returns_2(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    ghost = tmp_path / "ghost.py"
    rc = cli.main(["ci-check", "--manifesto", f"{ghost}:NoSuchClass"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "Could not resolve manifesto" in err


def test_cli_ci_check_nonzero_on_sovereignty_violation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(RuntimeScanner, "scan", lambda self: _dirty_scan())
    rc = cli.main(["ci-check"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
