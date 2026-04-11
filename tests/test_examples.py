"""
tests/test_examples.py
~~~~~~~~~~~~~~~~~~~~~~
Smoke-test each example as a subprocess. Catches regressions in the
runnable documentation alongside the library code.

Examples that require external services (OPA, PostgreSQL) skip
gracefully when those are unavailable — we expect exit 0 in all cases.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _run(script: str, *, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(EXAMPLES_DIR / script)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(cwd) if cwd else None,
        env=env,
    )


@pytest.mark.parametrize(
    "script",
    [
        "01_minimal_trace.py",
        "02_async_trace.py",
        "03_policy_simple_rule.py",
        "04_policy_rego.py",       # skips gracefully without OPA
        "05_kill_switch.py",
        "06_filesystem_storage.py",
        "07_postgresql_storage.py", # skips gracefully without psycopg2/DSN
        "08_langchain_agent.py",
        "09_otel_export.py",
        "10_manifesto.py",
        "11_compliance_report.py",
        "12_sovereignty_scan.py",
        "13_full_pipeline.py",
    ],
)
def test_example_runs_and_exits_zero(script: str, tmp_path: Path) -> None:
    result = _run(script, cwd=tmp_path)
    assert result.returncode == 0, (
        f"{script} exited {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


def test_example_01_prints_a_trace(tmp_path: Path) -> None:
    result = _run("01_minimal_trace.py", cwd=tmp_path)
    assert result.returncode == 0
    assert "trace_id" in result.stdout
    assert "schema_version" in result.stdout


def test_example_05_blocks_then_resumes(tmp_path: Path) -> None:
    result = _run("05_kill_switch.py", cwd=tmp_path)
    assert result.returncode == 0
    assert "kill switch ENGAGED" in result.stdout
    assert "kill switch DISENGAGED" in result.stdout
    assert "3 calls blocked" in result.stdout


def test_example_10_manifesto_shows_score(tmp_path: Path) -> None:
    result = _run("10_manifesto.py", cwd=tmp_path)
    assert result.returncode == 0
    assert "Overall score" in result.stdout
    assert "Days to enforcement" in result.stdout


def test_example_13_full_pipeline_sovereignty(tmp_path: Path) -> None:
    result = _run("13_full_pipeline.py", cwd=tmp_path)
    assert result.returncode == 0
    assert "FULL PIPELINE RESULT" in result.stdout
    assert "Sovereignty score" in result.stdout
