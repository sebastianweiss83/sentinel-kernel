"""Chain verification — walk attestations back to genesis.

A chain is a list of attestation envelopes sharing the same
``chain_namespace``. :func:`verify_chain` validates three properties:

1. Each envelope's own ``attestation_hash`` matches its content.
2. Each envelope's ``previous_hash`` equals the prior envelope's
   ``attestation_hash`` — or, for the first envelope in the list, the
   deterministic genesis hash of the shared namespace.
3. All envelopes share the same ``chain_namespace`` value.

The verifier is fully offline. It requires only the list of
attestations and the namespace definition (which can be read from
the first envelope).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentinel.chain.namespace import compute_genesis_hash
from sentinel.core.attestation import _hash_document, verify_attestation


@dataclass
class ChainVerification:
    """Outcome of :func:`verify_chain`."""

    verified: bool
    steps_checked: int
    detail: str
    first_failure_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "steps_checked": self.steps_checked,
            "detail": self.detail,
            "first_failure_index": self.first_failure_index,
        }


def verify_chain(attestations: list[dict[str, Any]]) -> ChainVerification:
    """Verify a list of attestations forms a valid chain back to genesis.

    :param attestations: attestations in chain order — earliest first,
        latest last. The list must not be empty.
    :returns: :class:`ChainVerification` describing the outcome.
    """
    if not attestations:
        return ChainVerification(
            verified=False,
            steps_checked=0,
            detail="chain is empty",
        )

    namespace = attestations[0].get("chain_namespace")
    if not namespace:
        return ChainVerification(
            verified=False,
            steps_checked=0,
            detail="first attestation has no chain_namespace",
            first_failure_index=0,
        )

    expected_previous = compute_genesis_hash(namespace)

    for idx, attestation in enumerate(attestations):
        if attestation.get("chain_namespace") != namespace:
            return ChainVerification(
                verified=False,
                steps_checked=idx,
                detail=(
                    f"chain_namespace drift at index {idx}: "
                    f"expected {namespace!r}, got "
                    f"{attestation.get('chain_namespace')!r}"
                ),
                first_failure_index=idx,
            )

        own = verify_attestation(attestation)
        if not own.valid:
            return ChainVerification(
                verified=False,
                steps_checked=idx,
                detail=f"attestation {idx} failed self-check: {own.detail}",
                first_failure_index=idx,
            )

        actual_previous = attestation.get("previous_hash")
        if actual_previous != expected_previous:
            return ChainVerification(
                verified=False,
                steps_checked=idx,
                detail=(
                    f"previous_hash mismatch at index {idx}: expected "
                    f"{expected_previous!r}, got {actual_previous!r}"
                ),
                first_failure_index=idx,
            )

        # The content hash was already verified by verify_attestation;
        # the chain-next expectation is the current envelope's own
        # attestation_hash.
        content = {k: v for k, v in attestation.items() if k != "attestation_hash"}
        expected_previous = _hash_document(content)
        assert expected_previous == attestation["attestation_hash"]  # consistency

    return ChainVerification(
        verified=True,
        steps_checked=len(attestations),
        detail=f"chain of {len(attestations)} attestations verified to genesis",
    )


__all__ = [
    "ChainVerification",
    "verify_chain",
]
