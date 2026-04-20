"""sentinel.comply — export evidence packs for regulators.

This module exposes the *Comply* verb of the canonical
Trace → Attest → Audit → Comply lifecycle. It aggregates decision
records and attestations into auditor-grade evidence packs — the
artefact a regulator or internal audit function accepts.

Example
-------
.. code-block:: python

    from sentinel import Sentinel
    from sentinel import comply

    sentinel = Sentinel()
    pack_path = comply.export(sentinel, "audit-q2.pdf")

Sovereignty guarantees
----------------------
Fully offline. No network calls. The generated PDF is
self-contained — an auditor can verify the hash manifest with only
the artefact in hand.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from sentinel.compliance.evidence_pack import (
    EvidencePackOptions,
    render_evidence_pdf,
)

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel
    from sentinel.manifesto import SentinelManifesto


def export(
    sentinel: Sentinel,
    output: str | Path,
    *,
    options: EvidencePackOptions | None = None,
    manifesto: SentinelManifesto | None = None,
    **option_overrides: Any,
) -> Path:
    """Export a signed PDF evidence pack.

    Wraps :func:`render_evidence_pdf`. When ``options`` is not
    provided, a default :class:`EvidencePackOptions` is constructed
    and any ``option_overrides`` keyword arguments are applied to
    it — a convenience for simple call sites.

    :param sentinel: configured :class:`Sentinel` instance.
    :param output: path to write the PDF.
    :param options: window + scope controls. Defaults to a fresh
        :class:`EvidencePackOptions` patched with any keyword overrides.
    :param manifesto: optional :class:`SentinelManifesto` — included
        in the sovereign attestation appendix.
    :param option_overrides: keyword shortcuts that set attributes on
        a default ``options`` instance (ignored when ``options`` is
        provided explicitly).
    :raises ImportError: if reportlab is not installed.
    :returns: the path the PDF was written to.
    """
    if options is None:
        options = EvidencePackOptions(**option_overrides)
    elif option_overrides:
        raise TypeError(
            "sentinel.comply.export received both `options` and keyword "
            "option overrides; pass one or the other."
        )

    return render_evidence_pdf(sentinel, options, output, manifesto=manifesto)


def sign(
    pdf_path: str | Path,
    output_path: str | Path | None = None,
    *,
    reason: str = "Sentinel evidence pack signature",
    location: str = "sentinel-kernel",
) -> Path:
    """PAdES-sign an evidence-pack PDF.

    Uses the default self-signed cert at
    ``~/.sentinel/pdf_cert.pem`` — auto-created on first use. For
    real-root-trust scenarios build a :class:`PAdESSigner` explicitly
    via :meth:`PAdESSigner.from_paths`.

    :param pdf_path: the PDF to sign.
    :param output_path: where to write the signed PDF. Defaults to a
        sibling path with ``.signed.pdf`` suffix.
    :returns: the path the signed PDF was written to.
    :raises RuntimeError: if the PAdES extra is not installed or the
        default cert path is unwriteable.
    """
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
    """Verify the PAdES signature(s) on a PDF.

    :returns: :class:`PDFSignatureVerification` describing the outcome.
    :raises RuntimeError: if the PAdES extra is not installed.
    """
    from sentinel.crypto.pades_signer import PAdESSigner

    # Construct a throwaway signer just to reuse the class's verify
    # method — verification only needs the PDF, not a key.
    signer = PAdESSigner.from_default_cert()
    if signer is None:  # pragma: no cover - only hit when extra missing
        raise RuntimeError(
            "PAdES verification requires the `[pades]` or `[pdf]` extra. "
            "Install: pip install 'sentinel-kernel[pdf]'"
        )
    return signer.verify_pdf(pdf_path)


if TYPE_CHECKING:
    from sentinel.crypto.pades_signer import PDFSignatureVerification


__all__ = [
    "EvidencePackOptions",
    "export",
    "sign",
    "verify",
]
