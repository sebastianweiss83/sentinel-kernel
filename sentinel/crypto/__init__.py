"""Cryptographic primitives for Sentinel.

- :class:`Ed25519Signer` — v3.4 default attestation signer.
  Install: ``pip install 'sentinel-kernel[ed25519]'`` (bundled in
  ``[pdf]`` and ``[dev]``).
- :class:`QuantumSafeSigner` — optional post-quantum (ML-DSA-65)
  signer for long-term retention scenarios.
  Install: ``pip install 'sentinel-kernel[pqc]'``.
- :class:`RFC3161Timestamper` — EU-sovereign RFC-3161 timestamping
  for evidence-pack cosignature.
"""

from sentinel.crypto.ed25519_signer import Ed25519Signer
from sentinel.crypto.signing import QuantumSafeSigner
from sentinel.crypto.timestamp import (
    NON_SOVEREIGN_TSAS,
    SOVEREIGN_TSAS,
    RFC3161Timestamper,
    TimestampToken,
)

__all__ = [
    "Ed25519Signer",
    "QuantumSafeSigner",
    "RFC3161Timestamper",
    "TimestampToken",
    "SOVEREIGN_TSAS",
    "NON_SOVEREIGN_TSAS",
]
