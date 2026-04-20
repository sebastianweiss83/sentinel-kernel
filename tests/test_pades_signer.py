"""Tests for PAdES PDF signing (v3.4 Evidence Release, Phase 6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel import cli, comply
from sentinel.crypto.pades_signer import (
    PAdESSigner,
    PDFSignatureVerification,
    _default_cert_paths,
)

pytest.importorskip("reportlab")
pytest.importorskip("pyhanko")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pdf(path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawString(100, 750, "Sentinel Evidence Pack — test fixture")
    c.showPage()
    c.save()


# ---------------------------------------------------------------------------
# PAdESSigner — constructors and self-signed cert generation
# ---------------------------------------------------------------------------


def test_generate_self_signed_returns_pem_pair() -> None:
    cert_pem, key_pem = PAdESSigner.generate_self_signed()
    assert cert_pem.startswith(b"-----BEGIN CERTIFICATE-----")
    assert key_pem.startswith(b"-----BEGIN PRIVATE KEY-----")


def test_from_paths_loads_generated_cert(tmp_path: Path) -> None:
    cert_pem, key_pem = PAdESSigner.generate_self_signed()
    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "cert.key"
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)

    signer = PAdESSigner.from_paths(cert_path, key_path)
    assert signer is not None


def test_from_default_cert_creates_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cert = tmp_path / "custom.pem"
    key = tmp_path / "custom.key"
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(cert))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(key))

    signer = PAdESSigner.from_default_cert()
    assert signer is not None
    assert cert.exists()
    assert key.exists()


def test_from_default_cert_reuses_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cert = tmp_path / "reuse.pem"
    key = tmp_path / "reuse.key"
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(cert))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(key))

    _ = PAdESSigner.from_default_cert()
    first_bytes = cert.read_bytes()

    # Second load must NOT regenerate — same cert file contents.
    _ = PAdESSigner.from_default_cert()
    assert cert.read_bytes() == first_bytes


def test_from_default_cert_honours_create_if_missing_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cert = tmp_path / "does-not-exist.pem"
    key = tmp_path / "does-not-exist.key"
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(cert))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(key))

    result = PAdESSigner.from_default_cert(create_if_missing=False)
    assert result is None
    assert not cert.exists()


def test_from_default_cert_returns_none_on_filesystem_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Point cert path at an unwriteable location (parent is a regular file).
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"blocker")
    bad_cert = blocker / "cert.pem"
    bad_key = blocker / "cert.key"
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(bad_cert))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(bad_key))

    assert PAdESSigner.from_default_cert() is None


def test_default_cert_paths_respects_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", "/tmp/a.pem")
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", "/tmp/a.key")
    cert, key = _default_cert_paths()
    assert cert == Path("/tmp/a.pem")
    assert key == Path("/tmp/a.key")


def test_default_cert_paths_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SENTINEL_PDF_CERT_PATH", raising=False)
    monkeypatch.delenv("SENTINEL_PDF_CERT_KEY_PATH", raising=False)
    cert, key = _default_cert_paths()
    assert cert.name == "pdf_cert.pem"
    assert key.name == "pdf_cert.key"


# ---------------------------------------------------------------------------
# sign_pdf / verify_pdf round-trip
# ---------------------------------------------------------------------------


def test_sign_pdf_produces_valid_signed_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(tmp_path / "c.pem"))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(tmp_path / "c.key"))

    pdf = tmp_path / "test.pdf"
    _make_pdf(pdf)

    signer = PAdESSigner.from_default_cert()
    assert signer is not None
    out = tmp_path / "test.signed.pdf"
    result = signer.sign_pdf(pdf, out)
    assert result == out
    assert out.exists()
    assert out.read_bytes().startswith(b"%PDF-")

    verification = signer.verify_pdf(out)
    assert verification.valid is True
    assert verification.signature_count == 1


def test_verify_pdf_on_unsigned_returns_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(tmp_path / "c.pem"))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(tmp_path / "c.key"))

    pdf = tmp_path / "unsigned.pdf"
    _make_pdf(pdf)

    signer = PAdESSigner.from_default_cert()
    assert signer is not None
    result = signer.verify_pdf(pdf)
    assert result.valid is False
    assert result.signature_count == 0


def test_pdf_signature_verification_to_dict() -> None:
    v = PDFSignatureVerification(
        valid=True, signature_count=2, detail="ok"
    )
    assert v.to_dict() == {
        "valid": True,
        "signature_count": 2,
        "detail": "ok",
    }


# ---------------------------------------------------------------------------
# sentinel.comply.sign / verify convenience wrappers
# ---------------------------------------------------------------------------


def test_comply_sign_default_output_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(tmp_path / "c.pem"))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(tmp_path / "c.key"))

    pdf = tmp_path / "pack.pdf"
    _make_pdf(pdf)

    signed = comply.sign(pdf)
    assert signed == pdf.with_suffix(".signed.pdf")
    assert signed.exists()


def test_comply_sign_explicit_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(tmp_path / "c.pem"))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(tmp_path / "c.key"))

    pdf = tmp_path / "pack.pdf"
    _make_pdf(pdf)
    out = tmp_path / "custom-signed.pdf"

    signed = comply.sign(pdf, out)
    assert signed == out
    assert out.exists()


def test_comply_verify_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(tmp_path / "c.pem"))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(tmp_path / "c.key"))

    pdf = tmp_path / "pack.pdf"
    _make_pdf(pdf)
    signed = comply.sign(pdf)

    result = comply.verify(signed)
    assert result.valid is True


# ---------------------------------------------------------------------------
# CLI — sentinel comply sign / verify
# ---------------------------------------------------------------------------


def test_cli_comply_sign_and_verify(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(tmp_path / "c.pem"))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(tmp_path / "c.key"))

    pdf = tmp_path / "pack.pdf"
    _make_pdf(pdf)

    rc = cli.main(["comply", "sign", str(pdf)])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    signed = pdf.with_suffix(".signed.pdf")
    assert signed.exists()

    rc = cli.main(["comply", "verify", str(signed), "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["valid"] is True


def test_cli_comply_sign_missing_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(["comply", "sign", str(tmp_path / "nope.pdf")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "not found" in captured.err


def test_cli_comply_verify_missing_input(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(["comply", "verify", str(tmp_path / "nope.pdf")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "not found" in captured.err


def test_cli_comply_verify_unsigned_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(tmp_path / "c.pem"))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(tmp_path / "c.key"))

    pdf = tmp_path / "unsigned.pdf"
    _make_pdf(pdf)

    rc = cli.main(["comply", "verify", str(pdf)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "invalid" in captured.out


def test_cli_comply_no_subcommand(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli.main(["comply"])
    capsys.readouterr()
    assert rc == 1


def test_cli_comply_sign_explicit_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("SENTINEL_PDF_CERT_PATH", str(tmp_path / "c.pem"))
    monkeypatch.setenv("SENTINEL_PDF_CERT_KEY_PATH", str(tmp_path / "c.key"))

    pdf = tmp_path / "pack.pdf"
    _make_pdf(pdf)
    out = tmp_path / "out" / "signed.pdf"

    rc = cli.main(["comply", "sign", str(pdf), "--output", str(out)])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert out.exists()
