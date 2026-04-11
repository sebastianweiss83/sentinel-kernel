"""Tests for the manifesto CI check scripts.

Each script runs as a subprocess so we exercise the exit-code contract
that CI depends on.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _run(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )


def test_check_sovereignty_script_exits_0() -> None:
    result = _run("check_sovereignty.py")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_check_license_script_exits_0() -> None:
    result = _run("check_license.py")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_check_manifesto_script_exits_0() -> None:
    result = _run("check_manifesto.py")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
