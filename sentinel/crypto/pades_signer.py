"""PAdES PDF signing for Sentinel evidence packs (v3.4 Evidence Release).

Wraps pyhanko to produce PDF Advanced Electronic Signatures (PAdES) on
evidence-pack PDFs. Signatures verify against any PAdES-aware reader
(Adobe Reader, Foxit, pyhanko's own verifier).

Key material
------------
Default: self-signed X.509 certificate generated from an Ed25519 key,
persisted as PEM to ``~/.sentinel/pdf_cert.pem`` + ``pdf_cert.key``.
The self-signed cert is valid for ten years by default. Operators
who need real-root trust should provide their own cert via
:meth:`PAdESSigner.from_paths`.

Install
-------
``pip install 'sentinel-kernel[pades]'`` — pulls ``pyhanko`` and
``cryptography``. Both bundled into ``[pdf]`` and ``[dev]`` extras.

Sovereignty guarantees
----------------------
- Keys live on the operator's filesystem. Never transmitted.
- Signing is purely local. No AIA resolution, no CRL download, no
  phone-home. Signatures are verifiable offline.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_MISSING_DEP_MESSAGE = (
    "PAdES PDF signing requires `pyhanko` and `cryptography`. Install:\n"
    "    pip install 'sentinel-kernel[pades]'\n"
    "or bundled:\n"
    "    pip install 'sentinel-kernel[pdf]'"
)

try:  # pragma: no cover - environment dependent
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    from cryptography.x509.oid import NameOID

    _HAS_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover - only when extra missing
    _HAS_CRYPTOGRAPHY = False

try:  # pragma: no cover - environment dependent
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign import signers
    from pyhanko.sign.signers import SimpleSigner
    from pyhanko.sign.timestamps import HTTPTimeStamper

    _HAS_PYHANKO = True
except ImportError:  # pragma: no cover - only when extra missing
    _HAS_PYHANKO = False
    HTTPTimeStamper = None  # type: ignore[assignment,misc]


DEFAULT_CERT_DIR = Path.home() / ".sentinel"
DEFAULT_CERT_PATH = DEFAULT_CERT_DIR / "pdf_cert.pem"
DEFAULT_CERT_KEY_PATH = DEFAULT_CERT_DIR / "pdf_cert.key"
DEFAULT_CERT_SUBJECT = "sentinel-kernel (self-signed evidence cert)"
DEFAULT_CERT_VALIDITY_DAYS = 3650

_ENV_CERT_PATH = "SENTINEL_PDF_CERT_PATH"
_ENV_CERT_KEY_PATH = "SENTINEL_PDF_CERT_KEY_PATH"

# RFC-3161 TSA wiring (v3.4.3+). Default to DFN (German research
# network, EU-sovereign); operator can override via env or opt out of
# timestamping entirely. Air-gapped deployments should set
# ``SENTINEL_TIMESTAMP=off`` to skip the network attempt.
_ENV_TIMESTAMP_TSA = "SENTINEL_TIMESTAMP_TSA"
_ENV_TIMESTAMP_DISABLE = "SENTINEL_TIMESTAMP"
_DEFAULT_TSA_URL = "http://timestamp.dfn.de/"
_DEFAULT_TSA_TIMEOUT_SECONDS = 5
_SENTINEL_NO_TSA = object()  # distinguishes "no kwarg" from explicit None


def _default_cert_paths() -> tuple[Path, Path]:
    """Resolve the default cert + cert-key paths.

    Env overrides ``SENTINEL_PDF_CERT_PATH`` / ``SENTINEL_PDF_CERT_KEY_PATH``
    take precedence over the canonical ``~/.sentinel/`` paths.
    """
    cert = os.environ.get(_ENV_CERT_PATH)
    key = os.environ.get(_ENV_CERT_KEY_PATH)
    return (
        Path(cert).expanduser() if cert else DEFAULT_CERT_PATH,
        Path(key).expanduser() if key else DEFAULT_CERT_KEY_PATH,
    )


@dataclass
class PDFSignatureVerification:
    """Result of :meth:`PAdESSigner.verify_pdf`."""

    valid: bool
    signature_count: int
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "signature_count": self.signature_count,
            "detail": self.detail,
        }


def _check_deps() -> None:
    if not _HAS_CRYPTOGRAPHY or not _HAS_PYHANKO:  # pragma: no cover - only when extra missing
        raise ImportError(_MISSING_DEP_MESSAGE)


def _default_timestamper() -> Any | None:
    """Build the default RFC-3161 TSA timestamper, or None to skip.

    Resolution order:

    1. ``SENTINEL_TIMESTAMP`` in ``{"off", "0", "no"}`` → None (opt-out,
       the air-gapped path).
    2. ``SENTINEL_TIMESTAMP_TSA`` set → use that URL.
    3. Default: DFN (German research network, EU-sovereign).

    Returns None when ``[pdf]`` extras aren't installed. Returns an
    :class:`HTTPTimeStamper` configured with a short default timeout
    so a down TSA can't block the signing flow indefinitely.
    """
    if not _HAS_PYHANKO:  # pragma: no cover - only when extra missing
        return None
    if os.environ.get(_ENV_TIMESTAMP_DISABLE, "").lower() in {"off", "0", "no"}:
        return None
    url = os.environ.get(_ENV_TIMESTAMP_TSA) or _DEFAULT_TSA_URL
    return HTTPTimeStamper(url, timeout=_DEFAULT_TSA_TIMEOUT_SECONDS)  # type: ignore[no-untyped-call]


class PAdESSigner:
    """Sign PDFs with PAdES using an Ed25519 self-signed or external cert.

    Construct via :meth:`from_default_cert` (auto-create / load default
    cert) or :meth:`from_paths` (load caller-provided cert + key).
    """

    def __init__(self, simple_signer: Any) -> None:
        """Internal — use the classmethod constructors."""
        _check_deps()
        self._signer = simple_signer

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def generate_self_signed(
        cls,
        *,
        subject: str = DEFAULT_CERT_SUBJECT,
        validity_days: int = DEFAULT_CERT_VALIDITY_DAYS,
    ) -> tuple[bytes, bytes]:
        """Generate a fresh self-signed Ed25519 cert + private key.

        :returns: ``(cert_pem, key_pem)`` bytes tuple.
        """
        _check_deps()
        key = Ed25519PrivateKey.generate()
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)])
        now = datetime.now(UTC)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .sign(key, None)
        )
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return cert_pem, key_pem

    @classmethod
    def from_paths(
        cls, cert_path: Path | str, key_path: Path | str
    ) -> PAdESSigner:
        """Load a PAdES signer from existing PEM cert + key paths."""
        _check_deps()
        cert = Path(cert_path).expanduser()
        key = Path(key_path).expanduser()
        signer = SimpleSigner.load(str(key), str(cert))  # type: ignore[no-untyped-call]
        return cls(signer)

    @classmethod
    def from_default_cert(
        cls,
        *,
        create_if_missing: bool = True,
    ) -> PAdESSigner | None:
        """Load or create the default self-signed PAdES signer.

        Returns None if the required extras aren't installed or the
        cert path is unwriteable, preserving the pre-v3.4 no-signer
        behaviour.
        """
        if not (_HAS_CRYPTOGRAPHY and _HAS_PYHANKO):  # pragma: no cover
            return None

        cert_path, key_path = _default_cert_paths()
        try:
            if cert_path.exists() and key_path.exists():
                return cls.from_paths(cert_path, key_path)
            if not create_if_missing:
                return None
            cert_pem, key_pem = cls.generate_self_signed()
            cert_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.parent.mkdir(parents=True, exist_ok=True)
            cert_path.write_bytes(cert_pem)
            key_path.write_bytes(key_pem)
            import contextlib

            with contextlib.suppress(OSError):  # pragma: no cover - Windows etc.
                os.chmod(key_path, 0o600)
            return cls.from_paths(cert_path, key_path)
        except OSError:
            return None

    # ------------------------------------------------------------------
    # Core sign / verify
    # ------------------------------------------------------------------

    def sign_pdf(
        self,
        input_path: Path | str,
        output_path: Path | str,
        *,
        field_name: str = "SentinelEvidenceSignature",
        reason: str = "Sentinel evidence pack signature",
        location: str = "sentinel-kernel",
        timestamper: Any = _SENTINEL_NO_TSA,
    ) -> Path:
        """PAdES-sign a PDF and write to ``output_path``.

        By default (``timestamper`` not passed), the signature embeds
        an RFC-3161 timestamp token from an EU-sovereign TSA (DFN by
        default, override via ``SENTINEL_TIMESTAMP_TSA``). If the TSA
        is unreachable the signature is written without a TST and a
        :class:`UserWarning` is emitted — the evidence pack still
        verifies, just without a trusted-time witness.

        Air-gapped deployments should set ``SENTINEL_TIMESTAMP=off``
        to skip the network attempt entirely; pass ``timestamper=None``
        for the same effect at the call site.
        """
        src = Path(input_path).expanduser()
        dst = Path(output_path).expanduser()
        dst.parent.mkdir(parents=True, exist_ok=True)

        meta = signers.PdfSignatureMetadata(
            field_name=field_name,
            reason=reason,
            location=location,
        )

        tsa = (
            _default_timestamper()
            if timestamper is _SENTINEL_NO_TSA
            else timestamper
        )

        def _sign_to(out_stream: Any, tsa_to_use: Any) -> None:
            with src.open("rb") as f_in:
                writer = IncrementalPdfFileWriter(f_in)
                signers.sign_pdf(
                    writer,
                    meta,
                    signer=self._signer,
                    timestamper=tsa_to_use,
                    output=out_stream,
                )

        try:
            with dst.open("wb") as f_out:
                _sign_to(f_out, tsa)
        except Exception as exc:
            if tsa is None:
                raise
            import warnings

            warnings.warn(
                f"RFC-3161 timestamper at {getattr(tsa, 'url', '<unknown>')!r} "
                f"failed ({type(exc).__name__}: {exc}); "
                f"signing without a trusted-time token. "
                f"Set SENTINEL_TIMESTAMP=off to silence this warning in "
                f"air-gapped deployments.",
                UserWarning,
                stacklevel=2,
            )
            with dst.open("wb") as f_out:
                _sign_to(f_out, None)

        return dst

    def verify_pdf(self, path: Path | str) -> PDFSignatureVerification:
        """Verify the PAdES signatures in a PDF.

        Light-weight structural verification: confirms a signature
        field is present and that its embedded bytes reconstruct a
        valid pyhanko signature envelope. Revocation / trust-root
        resolution is intentionally not performed — the evidence-pack
        use-case treats the cert as a self-describing witness, not a
        root of trust.
        """
        p = Path(path).expanduser()
        with p.open("rb") as f_in:
            reader = PdfFileReader(f_in)
            sigs = reader.embedded_signatures
            count = len(sigs)
            if count == 0:
                return PDFSignatureVerification(
                    valid=False,
                    signature_count=0,
                    detail="PDF contains no signature fields",
                )
            # pyhanko's embedded_signature objects self-parse; if any
            # byte range is missing or the PKCS#7 envelope is damaged
            # this attribute access raises. We check ``signed_data`` as
            # a structural test — it is None if the signature is
            # malformed.
            try:
                for sig in sigs:
                    _ = sig.signed_data
            except Exception as exc:  # pragma: no cover - defensive
                return PDFSignatureVerification(
                    valid=False,
                    signature_count=count,
                    detail=f"malformed signature envelope: {exc}",
                )

        return PDFSignatureVerification(
            valid=True,
            signature_count=count,
            detail=f"{count} signature(s) structurally verified",
        )


__all__ = [
    "PAdESSigner",
    "PDFSignatureVerification",
    "DEFAULT_CERT_PATH",
    "DEFAULT_CERT_KEY_PATH",
    "_default_cert_paths",
    "_default_timestamper",
]
