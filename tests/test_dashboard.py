"""
tests/test_dashboard.py
~~~~~~~~~~~~~~~~~~~~~~~
Tests for the terminal dashboard, HTML report, and CLI.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from sentinel import Sentinel
from sentinel.cli import main as cli_main
from sentinel.dashboard import HTMLReport, TerminalDashboard
from sentinel.manifesto import EUOnly, SentinelManifesto
from sentinel.storage import SQLiteStorage


def _sentinel() -> Sentinel:
    return Sentinel(storage=SQLiteStorage(":memory:"), project="dash-test")


# ---------------------------------------------------------------------------
# Terminal dashboard
# ---------------------------------------------------------------------------


def test_terminal_dashboard_initializes() -> None:
    dash = TerminalDashboard(_sentinel())
    frame = dash.render_once()
    assert "SENTINEL SOVEREIGNTY DASHBOARD" in frame
    assert "dash-test" in frame
    assert "Kill switch" in frame


def test_terminal_dashboard_reflects_kill_switch_state() -> None:
    sentinel = _sentinel()
    dash = TerminalDashboard(sentinel)

    assert "normal" in dash.render_once() or "ENGAGED" not in dash.render_once()

    sentinel.engage_kill_switch("test halt")
    frame = dash.render_once()
    assert "ENGAGED" in frame


def test_terminal_dashboard_renders_trace_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = _sentinel()

    @sentinel.trace
    def do_work(x: int) -> dict[str, int]:
        return {"x": x}

    for i in range(3):
        do_work(i)

    dash = TerminalDashboard(sentinel)
    frame = dash.render_once()
    # three NOT_EVALUATED traces — show up under NO_POLICY
    assert "NO_POLICY" in frame


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------


def test_html_report_generated() -> None:
    html = HTMLReport().generate(_sentinel())
    assert "<html" in html
    assert "Sentinel Sovereignty Report" in html


def test_html_report_self_contained() -> None:
    html = HTMLReport().generate(_sentinel())
    # no external resource loads
    for needle in ('src="http', "src='http", 'href="http', "href='http", "cdn.", "@import url(http"):
        assert needle not in html.lower(), f"external reference found: {needle}"


def test_html_report_includes_all_sections() -> None:
    html = HTMLReport().generate(_sentinel())
    assert "EU AI Act compliance" in html
    assert "Runtime packages" in html
    assert "CI/CD findings" in html
    assert "Infrastructure findings" in html


def test_html_report_with_manifesto() -> None:
    class Clean(SentinelManifesto):
        jurisdiction = EUOnly()

    html = HTMLReport().generate(_sentinel(), manifesto=Clean())
    assert "Manifesto status" in html


def test_html_report_writes_to_file(tmp_path: Path) -> None:
    html = HTMLReport().generate(_sentinel())
    out = tmp_path / "report.html"
    out.write_text(html)
    assert out.stat().st_size > 0
    # re-read and sanity-check it's a real HTML file
    content = out.read_text()
    assert content.startswith("<!doctype html>")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _run_cli(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        code = cli_main(argv)
    finally:
        sys.stdout = old_stdout
    return code, buf.getvalue()


def test_cli_scan_command(tmp_path: Path) -> None:
    # run in an empty tmp dir so infra/cicd findings are stable
    code, out = _run_cli(["scan", "--repo", str(tmp_path)])
    assert code == 0
    assert "RUNTIME" in out


def test_cli_scan_json(tmp_path: Path) -> None:
    import json

    code, out = _run_cli(["scan", "--json", "--repo", str(tmp_path)])
    assert code == 0
    data = json.loads(out)
    assert "runtime" in data
    assert "cicd" in data
    assert "infrastructure" in data


def test_cli_compliance_command() -> None:
    code, out = _run_cli(["compliance", "check"])
    assert code == 0
    assert "EU AI ACT COMPLIANCE REPORT" in out


def test_cli_compliance_command_json() -> None:
    import json

    code, out = _run_cli(["compliance", "check", "--json"])
    assert code == 0
    data = json.loads(out)
    assert "overall" in data
    assert "articles" in data


def test_cli_report_command() -> None:
    code, out = _run_cli(["report"])
    assert code == 0
    assert "<html" in out
    assert "Sentinel Sovereignty Report" in out


def test_cli_report_writes_file(tmp_path: Path) -> None:
    out_path = tmp_path / "report.html"
    code, out = _run_cli(["report", "--output", str(out_path)])
    assert code == 0
    assert f"Wrote {out_path}" in out
    assert out_path.exists()
    assert "<html" in out_path.read_text()


def test_cli_dashboard_single_frame() -> None:
    code, out = _run_cli(["dashboard", "--frames", "1"])
    assert code == 0
    assert "SENTINEL SOVEREIGNTY DASHBOARD" in out
