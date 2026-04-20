"""sentinel.attest — cryptographic attestation of decision records.

This module exposes the *Attest* verb of the canonical
Trace → Attest → Audit → Comply lifecycle. An attestation is a
portable, JSON-serialisable envelope that binds a canonical hash to
the identity and configuration of the Sentinel instance at the
moment it was produced. The envelope is independently verifiable.

Example
-------
.. code-block:: python

    from sentinel import Sentinel
    from sentinel import attest

    sentinel = Sentinel()
    envelope = attest.generate(sentinel, title="Q2 governance attestation")
    result = attest.verify(envelope)
    assert result.valid

Sovereignty guarantees
----------------------
Fully offline. No network calls. Verification is deterministic and
reproducible from the envelope alone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sentinel.core.attestation import (
    AttestationResult,
    generate_attestation,
    verify_attestation,
)

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


def generate(
    sentinel: Sentinel,
    *,
    manifesto: Any | None = None,
    compliance_report: Any | None = None,
    title: str = "Sentinel Governance Attestation",
) -> dict[str, Any]:
    """Generate a portable, self-contained attestation envelope.

    The returned dict contains an ``attestation_hash`` field — a
    SHA-256 of all other fields (sorted keys, canonical JSON). Anyone
    can recompute the hash offline to verify the envelope is
    unmodified.

    :param sentinel: the configured :class:`Sentinel` instance.
    :param manifesto: optional :class:`SentinelManifesto` — included
        in the attestation summary.
    :param compliance_report: optional compliance report — its
        overall outcome is folded into the envelope.
    :param title: human-readable title for the envelope.
    :returns: attestation envelope (dict, portable, JSON-serialisable).
    """
    return generate_attestation(
        sentinel,
        manifesto=manifesto,
        compliance_report=compliance_report,
        title=title,
    )


def verify(attestation: dict[str, Any]) -> AttestationResult:
    """Verify an attestation envelope's integrity.

    Fully offline. Zero network calls. Returns an
    :class:`AttestationResult` indicating whether the envelope is
    valid and, if not, what failed.
    """
    return verify_attestation(attestation)


__all__ = [
    "AttestationResult",
    "generate",
    "verify",
    # Long-form aliases preserved for backward compatibility.
    "generate_attestation",
    "verify_attestation",
]
