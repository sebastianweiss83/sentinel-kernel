"""Namespace and genesis-hash helpers for the attestation chain.

An agent namespace is the tuple that groups attestations into a
single chain. The canonical serialisation is a colon-separated string
prefixed with ``sentinel-ns:v1:`` so that hash inputs are self-
describing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

NAMESPACE_PREFIX = "sentinel-ns:v1:"
GENESIS_PREFIX = "sentinel-genesis:"


@dataclass(frozen=True)
class ChainNamespace:
    """An attestation-chain namespace.

    Immutable and hashable — safe to use as a dict key.
    """

    agent_id: str
    jurisdiction: str
    policy_family: str

    def __post_init__(self) -> None:
        for field_name in ("agent_id", "jurisdiction", "policy_family"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"ChainNamespace.{field_name} must be a non-empty string; "
                    f"got {value!r}"
                )
            if ":" in value:
                raise ValueError(
                    f"ChainNamespace.{field_name} must not contain ':' "
                    f"(reserved as namespace field separator); got {value!r}"
                )

    def as_string(self) -> str:
        """Return the canonical ``sentinel-ns:v1:...`` serialisation."""
        return (
            f"{NAMESPACE_PREFIX}"
            f"{self.agent_id}:{self.jurisdiction}:{self.policy_family}"
        )


def _coerce_namespace(ns: ChainNamespace | str) -> str:
    if isinstance(ns, ChainNamespace):
        return ns.as_string()
    if isinstance(ns, str) and ns:
        return ns
    raise TypeError(
        f"namespace must be a ChainNamespace or non-empty string, got {ns!r}"
    )


def compute_genesis_hash(namespace: ChainNamespace | str) -> str:
    """Return the deterministic genesis hash for a namespace.

    Hash = SHA-256(``sentinel-genesis:`` + canonical-namespace-string).
    Recomputable by any verifier with only the namespace definition.
    """
    ns_str = _coerce_namespace(namespace)
    payload = f"{GENESIS_PREFIX}{ns_str}".encode()
    return hashlib.sha256(payload).hexdigest()


__all__ = [
    "ChainNamespace",
    "NAMESPACE_PREFIX",
    "GENESIS_PREFIX",
    "compute_genesis_hash",
]
