"""Comply verb of Trace → Attest → Audit → Comply.

Convenience wrappers for generating, signing, and verifying the
evidence-pack PDF a regulator accepts.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from sentinel.compliance.evidence_pack import EvidencePackOptions, render_evidence_pdf

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel
    from sentinel.crypto.pades_signer import PDFSignatureVerification
    from sentinel.manifesto import SentinelManifesto


def export(
    sentinel: Sentinel,
    output: str | Path,
    *,
    options: EvidencePackOptions | None = None,
    manifesto: SentinelManifesto | None = None,
    **option_overrides: Any,
) -> Path:
    """Write an evidence-pack PDF. Keyword args without ``options=``
    are forwarded to a default ``EvidencePackOptions``."""
    if options is None:
        options = EvidencePackOptions(**option_overrides)
    elif option_overrides:
        raise TypeError(
            "pass `options=` or keyword overrides, not both"
        )
    return render_evidence_pdf(sentinel, options, output, manifesto=manifesto)


def sign(
    pdf_path: str | Path,
    output_path: str | Path | None = None,
    *,
    reason: str = "Sentinel evidence pack signature",
    location: str = "sentinel-kernel",
) -> Path:
    """PAdES-sign a PDF using the default cert at ``~/.sentinel/pdf_cert.pem``."""
    from sentinel.crypto.pades_signer import PAdESSigner

    signer = PAdESSigner.from_default_cert()
    if signer is None:  # pragma: no cover - only hit when extra missing
        raise RuntimeError(
            "PAdES signing requires the `[pades]` or `[pdf]` extra. "
            "Install: pip install 'sentinel-kernel[pdf]'"
        )

    src = Path(pdf_path).expanduser()
    if output_path is None:
        output_path = src.with_suffix(".signed.pdf")
    return signer.sign_pdf(src, output_path, reason=reason, location=location)


def verify(pdf_path: str | Path) -> PDFSignatureVerification:
    """Structural PAdES check on a signed PDF."""
    from sentinel.crypto.pades_signer import PAdESSigner

    signer = PAdESSigner.from_default_cert()
    if signer is None:  # pragma: no cover - only hit when extra missing
        raise RuntimeError(
            "PAdES verification requires the `[pades]` or `[pdf]` extra. "
            "Install: pip install 'sentinel-kernel[pdf]'"
        )
    return signer.verify_pdf(pdf_path)


__all__ = ["EvidencePackOptions", "export", "sign", "verify"]
