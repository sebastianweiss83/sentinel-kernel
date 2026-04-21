"""Walk an attestation list back to genesis, rejecting tamper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentinel.chain.namespace import compute_genesis_hash
from sentinel.core.attestation import verify_attestation


@dataclass
class ChainVerification:
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
    """Check every envelope's self-hash and the chain linkage back to genesis.

    Attestations must be ordered earliest-first. The namespace is
    read from the first envelope; all envelopes must agree.
    """
    if not attestations:
        return ChainVerification(False, 0, "chain is empty")

    namespace = attestations[0].get("chain_namespace")
    if not namespace:
        return ChainVerification(
            False, 0, "first attestation has no chain_namespace",
            first_failure_index=0,
        )

    expected_previous = compute_genesis_hash(namespace)

    for idx, att in enumerate(attestations):
        if att.get("chain_namespace") != namespace:
            return ChainVerification(
                False, idx,
                f"chain_namespace drift at index {idx}: "
                f"expected {namespace!r}, got {att.get('chain_namespace')!r}",
                first_failure_index=idx,
            )

        own = verify_attestation(att)
        if not own.valid:
            return ChainVerification(
                False, idx,
                f"attestation {idx} failed self-check: {own.detail}",
                first_failure_index=idx,
            )

        if att.get("previous_hash") != expected_previous:
            return ChainVerification(
                False, idx,
                f"previous_hash mismatch at index {idx}: expected "
                f"{expected_previous!r}, got {att.get('previous_hash')!r}",
                first_failure_index=idx,
            )

        # Advance: the next envelope's previous_hash must be this
        # envelope's attestation_hash. verify_attestation has already
        # re-computed it.
        expected_previous = att["attestation_hash"]

    return ChainVerification(
        True, len(attestations),
        f"chain of {len(attestations)} attestations verified to genesis",
    )


__all__ = ["ChainVerification", "verify_chain"]
