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
from typing import TYPE_CHECKING, Any, Union

from sentinel.compliance.evidence_pack import (
    EvidencePackOptions,
    render_evidence_pdf,
)

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel
    from sentinel.manifesto import SentinelManifesto


def export(
    sentinel: "Sentinel",
    output: Union[str, Path],
    *,
    options: EvidencePackOptions | None = None,
    manifesto: "SentinelManifesto | None" = None,
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


__all__ = [
    "EvidencePackOptions",
    "export",
]
