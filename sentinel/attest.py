"""Attest verb of Trace → Attest → Audit → Comply.

Thin module around `sentinel.core.attestation.generate_attestation` /
`verify_attestation` — re-exported as `generate` / `verify` to match
the verb formula while keeping the long-form names importable.
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
    """Produce a portable attestation envelope for ``sentinel``."""
    return generate_attestation(
        sentinel,
        manifesto=manifesto,
        compliance_report=compliance_report,
        title=title,
    )


def verify(attestation: dict[str, Any]) -> AttestationResult:
    """Recompute the envelope's hash and report whether it still matches."""
    return verify_attestation(attestation)


__all__ = [
    "AttestationResult",
    "generate",
    "verify",
    "generate_attestation",
    "verify_attestation",
]
