"""Portable self-contained governance attestations.

Unlike cloud attestations that require an external service to verify,
Sentinel attestations are self-contained JSON documents verifiable
offline. No network call. No external service. No API key.

The ``attestation_hash`` IS the proof — recompute it from the document
content and compare. If hashes match, the document is unmodified.

Usage::

    from sentinel.core.attestation import (
        generate_attestation,
        verify_attestation,
    )

    attestation = generate_attestation(sentinel=my_sentinel)
    with open("governance.json", "w") as f:
        json.dump(attestation, f, indent=2)

    result = verify_attestation(attestation)
    assert result.valid, result.detail
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel

ATTESTATION_SCHEMA_VERSION = "1.0.0"
_HASH_KEY = "attestation_hash"


@dataclass
class AttestationResult:
    """Result of :func:`verify_attestation`."""

    valid: bool
    hash_verified: bool
    detail: str
    what_failed: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "hash_verified": self.hash_verified,
            "detail": self.detail,
            "what_failed": self.what_failed,
        }


def _hash_document(doc: dict[str, Any]) -> str:
    """Canonical SHA-256 of a dict, sorted keys, no trailing newline."""
    serialised = json.dumps(doc, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(serialised.encode()).hexdigest()


def generate_attestation(
    sentinel: Sentinel,
    manifesto: Any | None = None,
    compliance_report: Any | None = None,
    title: str = "Sentinel Governance Attestation",
    *,
    chain_namespace: "Any | None" = None,
    previous_hash: str | None = None,
) -> dict[str, Any]:
    """Generate a portable self-contained attestation document.

    The returned dict contains an ``attestation_hash`` field that is a
    SHA-256 of all other fields (sorted keys). Anyone can recompute
    the hash offline to verify the document is unmodified.

    When ``chain_namespace`` is provided, the envelope is linked into
    the attestation chain for that namespace: a ``previous_hash``
    field is populated. If ``previous_hash`` is not explicitly
    supplied, the deterministic genesis hash of the namespace is used
    (i.e. this is the first attestation in the chain).

    :param chain_namespace: a :class:`ChainNamespace` or its canonical
        string form.
    :param previous_hash: hex digest of the prior attestation in the
        same chain. Ignored when ``chain_namespace`` is None.
    """
    from sentinel import __version__ as sentinel_version

    trace_count = 0
    try:
        trace_count = len(sentinel.query(limit=10_000))
    except Exception:
        trace_count = 0

    sovereignty_assertions: list[str] = [
        "apache-2.0-licensed",
        "zero-us-cloud-act-in-critical-path",
        "air-gap-capable",
        "tamper-resistant-trace-schema",
    ]

    payload: dict[str, Any] = {
        "schema_version": ATTESTATION_SCHEMA_VERSION,
        "title": title,
        "generated_at": datetime.now(UTC).isoformat(),
        "sentinel_version": sentinel_version,
        "project": sentinel.project,
        "data_residency": sentinel.data_residency.value,
        "sovereign_scope": sentinel.sovereign_scope,
        "storage_backend": sentinel.storage.backend_name,
        "trace_count": trace_count,
        "sovereignty_assertions": sovereignty_assertions,
        "kill_switch_active": sentinel.kill_switch_active,
    }

    if chain_namespace is not None:
        from sentinel.chain.namespace import (
            _coerce_namespace,
            compute_genesis_hash,
        )

        ns_string = _coerce_namespace(chain_namespace)
        payload["chain_namespace"] = ns_string
        if previous_hash is None:
            payload["previous_hash"] = compute_genesis_hash(ns_string)
        else:
            payload["previous_hash"] = previous_hash

    if manifesto is not None:
        try:
            report = manifesto.check(sentinel=sentinel) if hasattr(manifesto, "check") else None
            if report is not None:
                payload["manifesto_summary"] = {
                    "overall_score": getattr(report, "overall_score", None),
                    "gap_count": len(getattr(report, "gaps", []) or []),
                    "acknowledged_gap_count": len(getattr(report, "acknowledged_gaps", []) or []),
                }
        except Exception as exc:
            payload["manifesto_summary"] = {"error": f"{type(exc).__name__}: {exc}"}

    if compliance_report is not None:
        try:
            payload["compliance_summary"] = {
                "overall": str(getattr(compliance_report, "overall", "unknown")),
                "automated_coverage": getattr(compliance_report, "automated_coverage", None),
                "days_to_enforcement": getattr(compliance_report, "days_to_enforcement", None),
            }
        except Exception as exc:
            payload["compliance_summary"] = {"error": f"{type(exc).__name__}: {exc}"}

    payload[_HASH_KEY] = _hash_document(payload)
    return payload


def verify_attestation(attestation: dict[str, Any]) -> AttestationResult:
    """Verify an attestation's hash matches its content.

    Fully offline. Zero network calls.
    """
    if not isinstance(attestation, dict):
        return AttestationResult(
            valid=False,
            hash_verified=False,
            detail="attestation must be a dict",
            what_failed="type",
        )

    stored = attestation.get(_HASH_KEY)
    if not stored:
        return AttestationResult(
            valid=False,
            hash_verified=False,
            detail="attestation has no attestation_hash",
            what_failed="missing_hash",
        )

    content = {k: v for k, v in attestation.items() if k != _HASH_KEY}
    computed = _hash_document(content)

    if computed != stored:
        return AttestationResult(
            valid=False,
            hash_verified=False,
            detail="hash mismatch — document has been modified",
            what_failed="hash",
        )

    return AttestationResult(
        valid=True,
        hash_verified=True,
        detail="attestation hash verified offline",
        what_failed=None,
    )
