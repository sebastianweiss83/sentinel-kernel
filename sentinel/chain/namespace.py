"""Agent-namespace identity and genesis-hash derivation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

NAMESPACE_PREFIX = "sentinel-ns:v1:"
GENESIS_PREFIX = "sentinel-genesis:"


@dataclass(frozen=True)
class ChainNamespace:
    """The tuple that groups attestations into a single chain.

    Immutable, hashable, usable as a dict key. Fields must be
    non-empty and must not contain ``:`` (reserved separator).
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
    """SHA-256 of ``sentinel-genesis:`` + the canonical namespace string.

    Any verifier with just the namespace definition can recompute this.
    """
    ns_str = _coerce_namespace(namespace)
    return hashlib.sha256(f"{GENESIS_PREFIX}{ns_str}".encode()).hexdigest()


__all__ = [
    "ChainNamespace",
    "NAMESPACE_PREFIX",
    "GENESIS_PREFIX",
    "compute_genesis_hash",
]
