"""
tests/test_demo.py
~~~~~~~~~~~~~~~~~~
Smoke tests for demo/demo_app.py — ensure it imports and runs end-to-end
without external services. The demo is the highest-leverage evaluation
artefact, so a broken demo is a shippable bug.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


DEMO_APP_PATH = Path(__file__).resolve().parents[1] / "demo" / "demo_app.py"


def _load_demo_module():
    spec = importlib.util.spec_from_file_location("demo_app", DEMO_APP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demo_app_imports_correctly() -> None:
    module = _load_demo_module()
    assert hasattr(module, "main")
    assert hasattr(module, "scenario_a_procurement")
    assert hasattr(module, "scenario_b_document_analysis")
    assert hasattr(module, "scenario_c_sovereignty_report")


def test_demo_scenarios_complete_without_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    # Ensure OTel wiring is skipped (no endpoint in the test env)
    monkeypatch.delenv("OTEL_ENDPOINT", raising=False)

    module = _load_demo_module()
    exit_code = module.main()
    assert exit_code == 0


def test_demo_produces_traces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OTEL_ENDPOINT", raising=False)

    module = _load_demo_module()
    module.main()

    out = capsys.readouterr().out
    assert "Scenario A" in out
    assert "Scenario B" in out
    assert "Scenario C" in out
    # SQLite file written
    db_file = tmp_path / "demo-output" / "sentinel-demo.db"
    assert db_file.exists()


def test_demo_sovereignty_report_generated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OTEL_ENDPOINT", raising=False)

    module = _load_demo_module()
    module.main()

    html_path = tmp_path / "demo-output" / "sovereignty_report.html"
    assert html_path.exists()
    html = html_path.read_text()
    assert "<html" in html
    assert "Sentinel Sovereignty Report" in html
    # Must be self-contained (air-gapped safe)
    assert "src=\"http" not in html
    assert "href=\"http" not in html

    manifesto_path = tmp_path / "demo-output" / "manifesto.json"
    assert manifesto_path.exists()
    import json
    data = json.loads(manifesto_path.read_text())
    assert "overall_score" in data
