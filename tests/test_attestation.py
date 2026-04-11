"""Tests for sentinel.core.attestation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sentinel import Sentinel, generate_attestation, verify_attestation
from sentinel.storage import SQLiteStorage

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sentinel() -> Sentinel:
    return Sentinel(storage=SQLiteStorage(":memory:"), project="att-test")


def test_generate_returns_dict(sentinel: Sentinel) -> None:
    doc = generate_attestation(sentinel=sentinel)
    assert isinstance(doc, dict)
    assert doc["schema_version"] == "1.0.0"
    assert doc["sentinel_version"]
    assert doc["project"] == "att-test"


def test_generate_includes_hash(sentinel: Sentinel) -> None:
    doc = generate_attestation(sentinel=sentinel)
    assert "attestation_hash" in doc
    assert len(doc["attestation_hash"]) == 64  # SHA-256 hex


def test_verify_valid_attestation(sentinel: Sentinel) -> None:
    doc = generate_attestation(sentinel=sentinel)
    result = verify_attestation(doc)
    assert result.valid is True
    assert result.hash_verified is True


def test_verify_tampered_fails(sentinel: Sentinel) -> None:
    doc = generate_attestation(sentinel=sentinel)
    doc["title"] = "tampered"
    result = verify_attestation(doc)
    assert result.valid is False
    assert result.what_failed == "hash"


def test_verify_missing_hash_fails() -> None:
    result = verify_attestation({"title": "no hash"})
    assert result.valid is False
    assert result.what_failed == "missing_hash"


def test_verify_non_dict_fails() -> None:
    result = verify_attestation("not a dict")  # type: ignore[arg-type]
    assert result.valid is False
    assert result.what_failed == "type"


def test_attestation_result_to_dict() -> None:
    from sentinel import AttestationResult

    r = AttestationResult(valid=True, hash_verified=True, detail="ok")
    d = r.to_dict()
    assert d["valid"] is True
    assert d["hash_verified"] is True
    assert d["what_failed"] is None


def test_generate_with_manifesto(sentinel: Sentinel) -> None:
    class _FakeReport:
        overall_score = 0.9
        gaps: list = []
        acknowledged_gaps: list = []

    class _FakeManifesto:
        def check(self, **_kwargs):
            return _FakeReport()

    doc = generate_attestation(sentinel=sentinel, manifesto=_FakeManifesto())
    assert "manifesto_summary" in doc
    assert doc["manifesto_summary"]["overall_score"] == 0.9


def test_generate_with_manifesto_error(sentinel: Sentinel) -> None:
    class _BrokenManifesto:
        def check(self, **_kwargs):
            raise RuntimeError("boom")

    doc = generate_attestation(sentinel=sentinel, manifesto=_BrokenManifesto())
    assert "error" in doc["manifesto_summary"]


def test_generate_with_compliance_report(sentinel: Sentinel) -> None:
    class _FakeCompliance:
        overall = "partial"
        automated_coverage = 0.75
        days_to_enforcement = 100

    doc = generate_attestation(sentinel=sentinel, compliance_report=_FakeCompliance())
    assert doc["compliance_summary"]["overall"] == "partial"
    assert doc["compliance_summary"]["days_to_enforcement"] == 100


def test_generate_with_compliance_report_error(sentinel: Sentinel) -> None:
    class _Broken:
        @property
        def overall(self):
            raise RuntimeError("property exploded")

    doc = generate_attestation(sentinel=sentinel, compliance_report=_Broken())
    assert "error" in doc["compliance_summary"]


def test_generate_handles_query_failure(
    sentinel: Sentinel, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(*_a, **_kw):
        raise RuntimeError("storage down")

    monkeypatch.setattr(sentinel, "query", _raise)
    doc = generate_attestation(sentinel=sentinel)
    assert doc["trace_count"] == 0


def test_attestation_airgap(
    sentinel: Sentinel, monkeypatch: pytest.MonkeyPatch
) -> None:
    import socket

    monkeypatch.setattr(
        socket.socket,
        "connect",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("net")),
    )
    doc = generate_attestation(sentinel=sentinel)
    assert verify_attestation(doc).valid


def test_cli_generate_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "att.json"
    result = subprocess.run(
        [sys.executable, "-m", "sentinel.cli", "attestation", "generate", "--output", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    doc = json.loads(out.read_text())
    assert "attestation_hash" in doc


def test_cli_verify_exits_0_on_valid(tmp_path: Path) -> None:
    out = tmp_path / "att.json"
    subprocess.run(
        [sys.executable, "-m", "sentinel.cli", "attestation", "generate", "--output", str(out)],
        cwd=ROOT,
        check=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "sentinel.cli", "attestation", "verify", "--input", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "valid:          True" in result.stdout


def test_cli_generate_main_inprocess(tmp_path: Path) -> None:
    """In-process call so coverage is measured."""
    from sentinel import cli

    out = tmp_path / "att.json"
    rc = cli.main(["attestation", "generate", "--output", str(out)])
    assert rc == 0
    assert out.exists()


def test_cli_generate_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    from sentinel import cli

    rc = cli.main(["attestation", "generate"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "attestation_hash" in out


def test_cli_generate_with_compliance(tmp_path: Path) -> None:
    from sentinel import cli

    out = tmp_path / "att.json"
    rc = cli.main(["attestation", "generate", "--output", str(out), "--compliance"])
    assert rc == 0
    doc = json.loads(out.read_text())
    assert "compliance_summary" in doc


def test_cli_verify_main_inprocess(tmp_path: Path) -> None:
    from sentinel import cli

    out = tmp_path / "att.json"
    cli.main(["attestation", "generate", "--output", str(out)])
    rc = cli.main(["attestation", "verify", "--input", str(out)])
    assert rc == 0


def test_cli_verify_main_inprocess_missing(tmp_path: Path) -> None:
    from sentinel import cli

    rc = cli.main(["attestation", "verify", "--input", str(tmp_path / "missing.json")])
    assert rc == 2


def test_cli_verify_main_inprocess_tampered(tmp_path: Path) -> None:
    from sentinel import cli

    out = tmp_path / "att.json"
    cli.main(["attestation", "generate", "--output", str(out)])
    doc = json.loads(out.read_text())
    doc["title"] = "tampered"
    out.write_text(json.dumps(doc))
    rc = cli.main(["attestation", "verify", "--input", str(out)])
    assert rc == 1


def test_cli_attestation_no_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    from sentinel import cli

    rc = cli.main(["attestation"])
    assert rc == 1


def test_cli_verify_fails_on_tampered(tmp_path: Path) -> None:
    out = tmp_path / "att.json"
    subprocess.run(
        [sys.executable, "-m", "sentinel.cli", "attestation", "generate", "--output", str(out)],
        cwd=ROOT,
        check=True,
    )
    doc = json.loads(out.read_text())
    doc["title"] = "tampered"
    out.write_text(json.dumps(doc))
    result = subprocess.run(
        [sys.executable, "-m", "sentinel.cli", "attestation", "verify", "--input", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
