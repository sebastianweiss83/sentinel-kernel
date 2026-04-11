"""
tests/test_coverage_gaps.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Targeted tests to raise five modules to 95%+ coverage:

    sentinel/dashboard/html.py        89% → 95%+
    sentinel/dashboard/terminal.py    90% → 95%+
    sentinel/scanner/cicd.py          91% → 95%+
    sentinel/scanner/infrastructure.py 92% → 95%+
    sentinel/storage/sqlite.py        93% → 95%+

Each test block hits specific uncovered lines identified by
``pytest --cov-report=term-missing``.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.storage import SQLiteStorage


def _sentinel(tmp_path: Path) -> Sentinel:
    return Sentinel(
        storage=SQLiteStorage(str(tmp_path / "cov.db")),
        project="coverage-gap-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )


# ===========================================================================
# sentinel/dashboard/html.py
# ===========================================================================


def test_countdown_classes_negative_days_is_safe() -> None:
    from sentinel.dashboard.html import _countdown_classes

    assert _countdown_classes(-1) == "countdown safe"
    assert _countdown_classes(-999) == "countdown safe"


def test_countdown_classes_urgent_under_90_days() -> None:
    from sentinel.dashboard.html import _countdown_classes

    assert _countdown_classes(89) == "countdown urgent"
    assert _countdown_classes(1) == "countdown urgent"
    assert _countdown_classes(0) == "countdown urgent"


def test_countdown_classes_normal_above_90_days() -> None:
    from sentinel.dashboard.html import _countdown_classes

    assert _countdown_classes(90) == "countdown"
    assert _countdown_classes(365) == "countdown"


def test_status_priority_action_required_returns_medium() -> None:
    from sentinel.dashboard.html import _status_priority

    assert _status_priority("ACTION_REQUIRED") == ("medium", "MEDIUM")


def test_status_priority_unknown_status_returns_low() -> None:
    from sentinel.dashboard.html import _status_priority

    assert _status_priority("COMPLIANT") == ("low", "LOW")
    assert _status_priority("") == ("low", "LOW")
    assert _status_priority("SOMETHING_ELSE") == ("low", "LOW")


def test_html_report_covers_all_countdown_text_variants(
    tmp_path: Path,
) -> None:
    """Exercise the three countdown-text branches (in-force, <90, normal)."""
    from sentinel.dashboard.html import _render_html

    sentinel = _sentinel(tmp_path)

    fake_runtime = SimpleNamespace(
        sovereignty_score=1.0,
        total_packages=1,
        sovereign_packages=1,
        us_owned_packages=0,
        unknown_jurisdiction=0,
        critical_path_violations=[],
        packages=[],
    )
    fake_cicd = SimpleNamespace(findings=[])
    fake_infra = SimpleNamespace(findings=[])

    class _FakeArticle:
        def __init__(self, name):
            self.article = name
            self.title = "t"
            self.status = "COMPLIANT"
            self.detail = "d"
            self.automated = True

    fake_compliance = SimpleNamespace(
        days_to_enforcement=0,
        overall="COMPLIANT",
        automated_coverage=1.0,
        articles={"Art. 12": _FakeArticle("Art. 12")},
    )

    for days, expected_fragment in (
        (-1, "is now in force"),
        (30, "Less than 90 days"),
        (200, "2 August 2026"),
    ):
        fake_compliance.days_to_enforcement = days
        html = _render_html(
            sentinel=sentinel,
            runtime=fake_runtime,
            cicd=fake_cicd,
            infra=fake_infra,
            compliance=fake_compliance,
            manifesto_report=None,
        )
        assert expected_fragment in html


def test_html_report_exec_summary_all_three_ranges(tmp_path: Path) -> None:
    """Directly exercise the three executive-summary branches via _render_html."""
    from sentinel.dashboard.html import _render_html

    sentinel = _sentinel(tmp_path)
    fake_cicd = SimpleNamespace(findings=[])
    fake_infra = SimpleNamespace(findings=[])

    class _FakeArticle:
        def __init__(self, name):
            self.article = name
            self.title = "t"
            self.status = "COMPLIANT"
            self.detail = "d"
            self.automated = True

    fake_compliance = SimpleNamespace(
        days_to_enforcement=200,
        overall="COMPLIANT",
        automated_coverage=1.0,
        articles={"Art. 12": _FakeArticle("Art. 12")},
    )

    cases = [
        (0.95, "meets EU sovereignty requirements"),
        (0.75, "partially sovereign"),
        (0.40, "significant sovereignty gaps"),
    ]
    for score, fragment in cases:
        fake_runtime = SimpleNamespace(
            sovereignty_score=score,
            total_packages=10,
            sovereign_packages=int(10 * score),
            us_owned_packages=10 - int(10 * score),
            unknown_jurisdiction=0,
            critical_path_violations=[],
            packages=[],
        )
        html = _render_html(
            sentinel=sentinel,
            runtime=fake_runtime,
            cicd=fake_cicd,
            infra=fake_infra,
            compliance=fake_compliance,
            manifesto_report=None,
        )
        assert fragment in html, f"score {score} → expected {fragment!r}"


def test_html_report_us_package_row_rendering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inject a US-owned package so the cloud_act_exposure branch executes."""
    from sentinel.dashboard import HTMLReport
    from sentinel.scanner.runtime import PackageReport, RuntimeScanner, ScanResult

    fake_pkg = PackageReport(
        name="openai",
        version="1.0.0",
        parent_company="OpenAI",
        jurisdiction="US",
        cloud_act_exposure=True,
        in_critical_path=True,
        is_optional=False,
    )

    def fake_scan(self):
        return ScanResult(packages=[fake_pkg], critical_path_violations=["openai"])

    monkeypatch.setattr(RuntimeScanner, "scan", fake_scan)
    html = HTMLReport().generate(_sentinel(tmp_path))
    assert "openai" in html
    assert "OpenAI" in html
    # The row should carry the 'us' class (left-border accent)
    assert "class='us'" in html


def test_html_report_no_actions_when_all_compliant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force every EU AI Act article to COMPLIANT to hit the 'no actions' branch."""
    from sentinel.compliance import EUAIActChecker
    from sentinel.compliance.euaiact import ArticleReport
    from sentinel.dashboard import HTMLReport

    original_check = EUAIActChecker.check

    def patched_check(self, sentinel_instance, _orig=original_check):
        report = _orig(self, sentinel_instance)
        for art_name in list(report.articles.keys()):
            report.articles[art_name] = ArticleReport(
                article=art_name,
                title="Test",
                status="COMPLIANT",
                automated=True,
                detail="all good",
            )
        return report

    monkeypatch.setattr(EUAIActChecker, "check", patched_check)
    html = HTMLReport().generate(_sentinel(tmp_path))
    assert "No outstanding actions" in html


# ===========================================================================
# sentinel/dashboard/terminal.py
# ===========================================================================


def test_terminal_c_helper_respects_no_color(monkeypatch: pytest.MonkeyPatch) -> None:
    from sentinel.dashboard.terminal import _c

    monkeypatch.setenv("NO_COLOR", "1")
    assert _c("hello", "\x1b[32m") == "hello"  # no escape codes
    monkeypatch.delenv("NO_COLOR")
    # When NO_COLOR is unset, colours are applied
    coloured = _c("hello", "\x1b[32m")
    assert coloured.startswith("\x1b[32m") and "hello" in coloured


def test_terminal_width_handles_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the whole ``shutil`` binding on the terminal module only,
    so pytest's own terminal writer still sees the real ``shutil``.

    Previous version patched ``shutil.get_terminal_size`` globally,
    which crashed pytest's ``pytest_runtest_logreport`` when it tried
    to compute progress width.
    """
    import types

    from sentinel.dashboard import terminal

    fake_shutil = types.SimpleNamespace(
        get_terminal_size=lambda *a, **kw: (_ for _ in ()).throw(OSError("no tty")),
    )
    monkeypatch.setattr(terminal, "shutil", fake_shutil)
    assert terminal._terminal_width() == 80


def test_terminal_format_score_yellow_and_red() -> None:
    from sentinel.dashboard.terminal import _format_score

    green = _format_score(0.95)
    yellow = _format_score(0.75)
    red = _format_score(0.4)
    assert "\x1b[" in green
    assert "\x1b[" in yellow
    assert "\x1b[" in red
    # All three should be distinct
    assert green != yellow
    assert yellow != red


def test_terminal_print_summary(tmp_path: Path, capsys) -> None:
    from sentinel.dashboard import TerminalDashboard

    dash = TerminalDashboard(_sentinel(tmp_path))
    dash.print_summary()
    out = capsys.readouterr().out
    assert "SENTINEL SOVEREIGNTY DASHBOARD" in out


def test_terminal_run_stops_on_keyboard_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sentinel.dashboard import TerminalDashboard

    dash = TerminalDashboard(_sentinel(tmp_path))

    calls = {"n": 0}

    def fake_sleep(_s):
        calls["n"] += 1
        raise KeyboardInterrupt

    monkeypatch.setattr("sentinel.dashboard.terminal.time.sleep", fake_sleep)
    # Should return cleanly, not propagate KeyboardInterrupt
    dash.run(interval_s=0.01, max_frames=5)
    assert calls["n"] == 1


# ===========================================================================
# sentinel/scanner/cicd.py
# ===========================================================================


def test_cicd_scanner_detects_circleci(tmp_path: Path) -> None:
    from sentinel.scanner import CICDScanner

    (tmp_path / ".circleci").mkdir()
    (tmp_path / ".circleci" / "config.yml").write_text("version: 2.1\n")
    result = CICDScanner().scan(tmp_path)
    assert any(f.component == "circleci" for f in result.findings)


def test_cicd_scanner_detects_gitlab_ci(tmp_path: Path) -> None:
    from sentinel.scanner import CICDScanner

    (tmp_path / ".gitlab-ci.yml").write_text("stages: [test]\n")
    result = CICDScanner().scan(tmp_path)
    assert any(f.component == "gitlab_ci" for f in result.findings)


def test_cicd_scanner_makefile_handles_empty_lines(tmp_path: Path) -> None:
    from sentinel.scanner import CICDScanner

    (tmp_path / "Makefile").write_text(
        "\n"
        "\n"
        "test:\n"
        "\tpython -m pytest\n"
        "\n"
    )
    result = CICDScanner().scan(tmp_path)
    assert [f for f in result.findings if f.component == "makefile_download"] == []


def test_cicd_scanner_compose_skips_empty_image(tmp_path: Path) -> None:
    from sentinel.scanner import CICDScanner

    (tmp_path / "docker-compose.yml").write_text(
        "services:\n"
        "  app:\n"
        "    image: \n"  # empty — should be skipped
        "  real:\n"
        "    image: 'postgres:15.6-alpine'\n"
    )
    result = CICDScanner().scan(tmp_path)
    compose_findings = [
        f for f in result.findings if f.component == "docker_compose_image"
    ]
    assert len(compose_findings) == 1
    assert "postgres" in compose_findings[0].detail


def test_classify_docker_image_all_registries() -> None:
    from sentinel.scanner.cicd import _classify_docker_image

    cases = [
        ("public.ecr.aws/nginx/nginx:latest", "Amazon ECR"),
        ("amazon/aws-cli:latest", "Amazon ECR"),
        ("gcr.io/project/image:tag", "Google Container Registry"),
        ("us.gcr.io/project/image", "Google Container Registry"),
        ("myacr.azurecr.io/image:tag", "Azure Container Registry"),
        ("ghcr.io/org/image:tag", "GitHub Container Registry (Microsoft)"),
        ("quay.io/org/image:tag", "Quay.io (Red Hat / IBM)"),
        ("docker.io/library/nginx", "Docker Hub"),
        ("library/alpine", "Docker Hub"),
        ("nginx:latest", "Docker Hub"),  # bare name → Docker Hub
    ]
    for image, expected_vendor in cases:
        vendor, _, exposure = _classify_docker_image(image)
        assert vendor == expected_vendor, f"{image} → {vendor}"
        assert exposure is True


def test_classify_docker_image_unknown_registry() -> None:
    from sentinel.scanner.cicd import _classify_docker_image

    vendor, jurisdiction, exposure = _classify_docker_image(
        "registry.example.eu/my-app:1.0"
    )
    assert vendor == "Unknown registry"
    assert jurisdiction == "Unknown"
    assert exposure is False


# ===========================================================================
# sentinel/scanner/infrastructure.py
# ===========================================================================


def test_infra_scan_result_to_json(tmp_path: Path) -> None:
    from sentinel.scanner import InfrastructureScanner

    result = InfrastructureScanner().scan(tmp_path)
    payload = result.to_json()
    data = json.loads(payload)
    assert "files_scanned" in data
    assert "findings" in data


def test_infra_scanner_is_excluded_skips_venv_paths(tmp_path: Path) -> None:
    from sentinel.scanner import InfrastructureScanner

    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "ignored.tf").write_text('provider "aws" {}\n')
    # A real provider at root should be picked up
    (tmp_path / "main.tf").write_text('provider "aws" {}\n')

    result = InfrastructureScanner().scan(tmp_path)
    tf_findings = [
        f for f in result.findings if f.component == "terraform_provider_aws"
    ]
    # Only the root one should appear; the one in .venv is excluded
    assert len(tf_findings) == 1
    assert tf_findings[0].file == "main.tf"


def test_infra_scanner_excludes_yaml_inside_venv(tmp_path: Path) -> None:
    """Line 78: the yaml loop's _is_excluded continue branch.

    CI's clean workspace has no yaml files under .venv/, so this
    branch was previously uncovered there (local devs hit it
    incidentally via their real .venv). Force it deterministically.
    """
    from sentinel.scanner import InfrastructureScanner

    venv_lib = tmp_path / ".venv" / "lib"
    venv_lib.mkdir(parents=True)
    # A k8s-looking yaml buried in .venv — must be skipped.
    (venv_lib / "ignored.yaml").write_text(
        "apiVersion: storage.k8s.io/v1\n"
        "kind: StorageClass\n"
        "parameters:\n"
        "  storageClassName: gp3\n"
    )
    # A real k8s yaml at the repo root — must be picked up.
    (tmp_path / "real.yaml").write_text(
        "apiVersion: storage.k8s.io/v1\n"
        "kind: StorageClass\n"
        "parameters:\n"
        "  storageClassName: gp3\n"
    )

    result = InfrastructureScanner().scan(tmp_path)
    k8s_findings = [
        f for f in result.findings if f.component == "kubernetes_storage_class"
    ]
    assert len(k8s_findings) == 1
    assert k8s_findings[0].file == "real.yaml"


def test_infra_walk_files_returns_nothing_for_missing_root(tmp_path: Path) -> None:
    """_walk_files must short-circuit on a path that doesn't exist."""
    from sentinel.scanner.infrastructure import _walk_files

    missing = tmp_path / "does-not-exist"
    assert list(_walk_files(missing, ("*.tf",))) == []


def test_infra_walk_files_respects_max_depth(tmp_path: Path) -> None:
    """Files buried past max_depth must not be yielded."""
    from sentinel.scanner.infrastructure import _walk_files

    # depth 0: shallow.tf
    (tmp_path / "shallow.tf").write_text('provider "aws" {}\n')
    # depth 4: a/b/c/d/deep.tf — beyond default max_depth=3
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    (deep / "deep.tf").write_text('provider "aws" {}\n')

    results = sorted(p.name for p in _walk_files(tmp_path, ("*.tf",), max_depth=3))
    assert "shallow.tf" in results
    assert "deep.tf" not in results


def test_infra_scan_does_not_hang_on_large_dir(tmp_path: Path) -> None:
    """Sanity: scanning a tree with thousands of non-matching files finishes fast."""
    import time

    from sentinel.scanner import InfrastructureScanner

    # Create many irrelevant files in deeply nested dirs — pruning must
    # keep this bounded.
    for i in range(20):
        d = tmp_path / f"dir{i}" / "a" / "b" / "c"
        d.mkdir(parents=True)
        for j in range(50):
            (d / f"file{j}.py").write_text("# irrelevant\n")
    (tmp_path / "main.tf").write_text('provider "hetzner" {}\n')

    start = time.monotonic()
    result = InfrastructureScanner().scan(tmp_path)
    elapsed = time.monotonic() - start
    # Should complete in well under a second even with 1000 noise files.
    assert elapsed < 2.0
    assert result.max_depth_scanned == 3
    # Only the top-level .tf matters
    assert result.files_scanned == 1


def test_infra_deadline_unbounded_never_expires() -> None:
    from sentinel.scanner.infrastructure import _Deadline

    d = _Deadline(None)
    assert d.expired() is False


def test_infra_deadline_fires_after_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """_Deadline is purely time.monotonic-based — no signal handlers."""
    import time

    from sentinel.scanner.infrastructure import _Deadline

    fake_now = [1000.0]

    def _fake_monotonic() -> float:
        return fake_now[0]

    monkeypatch.setattr(time, "monotonic", _fake_monotonic)
    d = _Deadline(5.0)
    assert d.expired() is False
    fake_now[0] += 4.0
    assert d.expired() is False
    fake_now[0] += 2.0  # now 6s elapsed > 5s budget
    assert d.expired() is True


def test_infra_scan_timeout_returns_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the deadline fires mid-walk, scan() returns partial results
    with timed_out=True instead of blocking indefinitely."""
    from sentinel.scanner import InfrastructureScanner
    from sentinel.scanner import infrastructure as mod

    # Deadline that expires immediately — first check fires.
    class _ZeroBudget:
        def expired(self) -> bool:
            return True

    def _make_zero(*_args, **_kwargs):
        return _ZeroBudget()

    monkeypatch.setattr(mod, "_Deadline", _make_zero)

    result = InfrastructureScanner().scan(".", timeout_seconds=0.001)
    assert result.timed_out is True
    # to_dict must surface the deadline note
    assert result.to_dict()["timed_out"] is True
    assert "deadline" in result.to_dict()["scan_note"].lower()


def _make_phase_fixture(tmp_path: Path) -> None:
    """Fixture with one .tf, one k8s .yaml, and a .env — covers all 3 phases."""
    (tmp_path / "main.tf").write_text('provider "hetzner" {}\n')
    (tmp_path / "storage.yaml").write_text(
        "apiVersion: storage.k8s.io/v1\n"
        "kind: StorageClass\n"
        "parameters:\n"
        "  storageClassName: gp3\n"
    )
    (tmp_path / ".env").write_text("AWS_ACCESS_KEY_ID=x\n")


def _install_fake_deadline(
    monkeypatch: pytest.MonkeyPatch, expire_after_n_checks: int
) -> None:
    """Patch _Deadline so .expired() returns True after N total calls."""
    from sentinel.scanner import infrastructure as mod

    state = {"count": 0}

    class _Fake:
        def expired(self) -> bool:
            state["count"] += 1
            return state["count"] > expire_after_n_checks

    monkeypatch.setattr(mod, "_Deadline", lambda *_a, **_kw: _Fake())


def test_infra_scan_deadline_expires_mid_phase1(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Line 154: `break` inside phase 1 loop when deadline expires."""
    from sentinel.scanner import InfrastructureScanner

    _make_phase_fixture(tmp_path)
    # Order of expired() calls in phase 1 with one .tf file:
    #   1) inside _walk_files at start of walk
    #   2) inside the scan() loop body check after the first yield
    # Let the walk start (count=1 False) then break on the scan body check.
    _install_fake_deadline(monkeypatch, expire_after_n_checks=1)

    result = InfrastructureScanner().scan(str(tmp_path))
    assert result.timed_out is True


def test_infra_scan_deadline_expires_mid_phase2(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Lines 165 and 172-173: `break` inside phase 2 loop + short-circuit."""
    from sentinel.scanner import InfrastructureScanner

    _make_phase_fixture(tmp_path)
    # Phase 1 _walk_files call 1 (False), scan() loop body check 2 (False),
    # post-phase-1 check 3 (False), phase 2 _walk_files call 4 (False),
    # phase 2 loop body check 5 (True -> break), post-phase-2 check (True).
    _install_fake_deadline(monkeypatch, expire_after_n_checks=4)

    result = InfrastructureScanner().scan(str(tmp_path))
    assert result.timed_out is True


def test_infra_scan_deadline_expires_at_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Line 182: deadline fires only at the final post-phase-3 check."""
    from sentinel.scanner import InfrastructureScanner
    from sentinel.scanner import infrastructure as mod

    _make_phase_fixture(tmp_path)

    # For 1 tf + 1 yaml + 1 env fixture, scan() calls expired() in this
    # order: phase1 walk(1), phase1 body(2), phase1 post(3), phase2 walk(4),
    # phase2 body(5), phase2 post(6), phase3 post(7). Only call 7 should
    # return True so line 182 is exercised without short-circuiting earlier.
    state = {"count": 0}

    class _OnlyFinal:
        def expired(self) -> bool:
            state["count"] += 1
            return state["count"] >= 7

    monkeypatch.setattr(mod, "_Deadline", lambda *_a, **_kw: _OnlyFinal())

    result = InfrastructureScanner().scan(str(tmp_path))
    assert result.timed_out is True
    # Phases 1 and 2 completed cleanly, so findings exist
    assert result.files_scanned >= 2


def test_infra_scan_phase2_and_phase3_respect_deadline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Deadline must be honoured between phases even when phase 1 finds nothing."""
    from sentinel.scanner import InfrastructureScanner

    (tmp_path / "x.yaml").write_text("apiVersion: v1\nkind: StorageClass\n")
    (tmp_path / ".env").write_text("AWS_ACCESS_KEY_ID=x\n")

    _install_fake_deadline(monkeypatch, expire_after_n_checks=0)
    result = InfrastructureScanner().scan(str(tmp_path))
    assert result.timed_out is True


def test_infra_scan_timeout_none_is_unbounded() -> None:
    """timeout_seconds=None disables the deadline entirely."""
    from sentinel.scanner import InfrastructureScanner

    result = InfrastructureScanner().scan(".", timeout_seconds=None)
    assert result.timed_out is False


def test_infra_walk_files_respects_deadline() -> None:
    """_walk_files stops yielding as soon as the deadline has expired."""
    from sentinel.scanner.infrastructure import _walk_files

    class _AlwaysExpired:
        def expired(self) -> bool:
            return True

    results = list(
        _walk_files(
            Path("."),
            ("*.tf",),
            max_depth=3,
            deadline=_AlwaysExpired(),  # type: ignore[arg-type]
        )
    )
    assert results == []


def test_infra_looks_like_k8s_handles_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from sentinel.scanner.infrastructure import _looks_like_k8s

    class _BrokenPath:
        def read_text(self, errors: str = "replace") -> str:
            raise OSError("no read")

    assert _looks_like_k8s(_BrokenPath()) is False  # type: ignore[arg-type]


def test_infra_scanner_detects_azure_storage_class(tmp_path: Path) -> None:
    from sentinel.scanner import InfrastructureScanner

    (tmp_path / "azure-sc.yaml").write_text(
        "apiVersion: storage.k8s.io/v1\n"
        "kind: StorageClass\n"
        "metadata:\n"
        "  name: azure-ssd\n"
        "provisioner: kubernetes.io/azure-disk\n"
        "parameters:\n"
        "  storageClassName: azuredisk-premium\n"
    )
    result = InfrastructureScanner().scan(tmp_path)
    azure = [
        f for f in result.findings
        if f.component == "kubernetes_storage_class" and "Azure" in f.vendor
    ]
    assert len(azure) == 1


def test_infra_scanner_detects_gcp_storage_class(tmp_path: Path) -> None:
    from sentinel.scanner import InfrastructureScanner

    (tmp_path / "gcp-sc.yaml").write_text(
        "apiVersion: storage.k8s.io/v1\n"
        "kind: StorageClass\n"
        "metadata:\n"
        "  name: gcp-ssd\n"
        "parameters:\n"
        "  storageClassName: pd-ssd\n"
    )
    result = InfrastructureScanner().scan(tmp_path)
    gcp = [
        f for f in result.findings
        if f.component == "kubernetes_storage_class" and "Google" in f.vendor
    ]
    assert len(gcp) == 1


# ===========================================================================
# sentinel/storage/sqlite.py
# ===========================================================================


def test_sqlite_storage_close(tmp_path: Path) -> None:
    storage = SQLiteStorage(str(tmp_path / "close.db"))
    storage.initialise()
    storage.close()
    # Calling close twice is safe
    storage.close()


def test_sqlite_storage_repr(tmp_path: Path) -> None:
    storage = SQLiteStorage(str(tmp_path / "repr.db"))
    r = repr(storage)
    assert "SQLiteStorage" in r
    assert "repr.db" in r
