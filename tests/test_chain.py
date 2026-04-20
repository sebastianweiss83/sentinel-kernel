"""Tests for sentinel.chain — attestation hash-chain linkage.

Phase 5 of v3.4 "Evidence Release". Attestations within an agent
namespace are cryptographically linked via ``previous_hash``, anchored
to a deterministic genesis hash per namespace.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sentinel import Sentinel, cli
from sentinel.chain import (
    ChainNamespace,
    ChainVerification,
    compute_genesis_hash,
    verify_chain,
)
from sentinel.chain.namespace import (
    GENESIS_PREFIX,
    NAMESPACE_PREFIX,
    _coerce_namespace,
)
from sentinel.core.attestation import generate_attestation
from sentinel.storage import SQLiteStorage

# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------


def test_namespace_canonical_string() -> None:
    ns = ChainNamespace(
        agent_id="risk",
        jurisdiction="EU-DE",
        policy_family="bafin-bait-8",
    )
    assert ns.as_string() == f"{NAMESPACE_PREFIX}risk:EU-DE:bafin-bait-8"


def test_namespace_is_frozen_and_hashable() -> None:
    ns1 = ChainNamespace("a", "b", "c")
    ns2 = ChainNamespace("a", "b", "c")
    # Same tuple → same hash & equal.
    assert ns1 == ns2
    assert hash(ns1) == hash(ns2)
    # Usable as dict key.
    d = {ns1: 1}
    assert d[ns2] == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"agent_id": "", "jurisdiction": "EU", "policy_family": "x"},
        {"agent_id": "a", "jurisdiction": "", "policy_family": "x"},
        {"agent_id": "a", "jurisdiction": "EU", "policy_family": ""},
    ],
)
def test_namespace_rejects_empty_fields(kwargs: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        ChainNamespace(**kwargs)


def test_namespace_rejects_colon_in_fields() -> None:
    with pytest.raises(ValueError, match="must not contain ':'"):
        ChainNamespace("a:b", "EU", "x")


def test_coerce_namespace_accepts_string() -> None:
    assert _coerce_namespace("sentinel-ns:v1:a:b:c") == "sentinel-ns:v1:a:b:c"


def test_coerce_namespace_rejects_empty_and_non_string() -> None:
    with pytest.raises(TypeError):
        _coerce_namespace("")
    with pytest.raises(TypeError):
        _coerce_namespace(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Genesis hash
# ---------------------------------------------------------------------------


def test_genesis_hash_is_deterministic() -> None:
    ns = ChainNamespace("a", "b", "c")
    assert compute_genesis_hash(ns) == compute_genesis_hash(ns)


def test_genesis_hash_matches_spec() -> None:
    ns = ChainNamespace("risk", "EU-DE", "bafin-bait-8")
    expected = hashlib.sha256(
        (GENESIS_PREFIX + ns.as_string()).encode()
    ).hexdigest()
    assert compute_genesis_hash(ns) == expected


def test_genesis_hash_differs_by_namespace() -> None:
    ns1 = ChainNamespace("a", "b", "c")
    ns2 = ChainNamespace("a", "b", "d")
    assert compute_genesis_hash(ns1) != compute_genesis_hash(ns2)


def test_genesis_hash_accepts_string_form() -> None:
    ns = ChainNamespace("a", "b", "c")
    assert compute_genesis_hash(ns) == compute_genesis_hash(ns.as_string())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sentinel_instance() -> Sentinel:
    return Sentinel(storage=SQLiteStorage(":memory:"), project="chain-test")


@pytest.fixture
def namespace() -> ChainNamespace:
    return ChainNamespace(
        agent_id="risk",
        jurisdiction="EU-DE",
        policy_family="bafin-bait-8",
    )


# ---------------------------------------------------------------------------
# Attestation envelope — previous_hash + chain_namespace
# ---------------------------------------------------------------------------


def test_first_attestation_uses_genesis(
    sentinel_instance: Sentinel, namespace: ChainNamespace
) -> None:
    envelope = generate_attestation(sentinel_instance, chain_namespace=namespace)
    assert envelope["chain_namespace"] == namespace.as_string()
    assert envelope["previous_hash"] == compute_genesis_hash(namespace)


def test_subsequent_attestation_uses_prior_hash(
    sentinel_instance: Sentinel, namespace: ChainNamespace
) -> None:
    a1 = generate_attestation(sentinel_instance, chain_namespace=namespace)
    a2 = generate_attestation(
        sentinel_instance,
        chain_namespace=namespace,
        previous_hash=a1["attestation_hash"],
    )
    assert a2["previous_hash"] == a1["attestation_hash"]


def test_attestation_without_namespace_has_no_chain_fields(
    sentinel_instance: Sentinel,
) -> None:
    envelope = generate_attestation(sentinel_instance)
    assert "chain_namespace" not in envelope
    assert "previous_hash" not in envelope


def test_attestation_envelope_hash_covers_chain_fields(
    sentinel_instance: Sentinel, namespace: ChainNamespace
) -> None:
    envelope = generate_attestation(sentinel_instance, chain_namespace=namespace)
    # Mutating the chain fields after the fact must break self-verify.
    from sentinel.core.attestation import verify_attestation

    envelope["previous_hash"] = "deadbeef"
    result = verify_attestation(envelope)
    assert result.valid is False


# ---------------------------------------------------------------------------
# Chain verification
# ---------------------------------------------------------------------------


def _build_chain(
    s: Sentinel, ns: ChainNamespace, length: int
) -> list[dict]:
    chain: list[dict] = []
    previous_hash: str | None = None
    for i in range(length):
        env = generate_attestation(
            s,
            chain_namespace=ns,
            previous_hash=previous_hash,
            title=f"attestation {i}",
        )
        chain.append(env)
        previous_hash = env["attestation_hash"]
    return chain


def test_verify_chain_genesis_only(
    sentinel_instance: Sentinel, namespace: ChainNamespace
) -> None:
    chain = _build_chain(sentinel_instance, namespace, 1)
    result = verify_chain(chain)
    assert result.verified is True
    assert result.steps_checked == 1


def test_verify_chain_multi_step(
    sentinel_instance: Sentinel, namespace: ChainNamespace
) -> None:
    chain = _build_chain(sentinel_instance, namespace, 4)
    result = verify_chain(chain)
    assert result.verified is True
    assert result.steps_checked == 4


def test_verify_chain_detects_tamper(
    sentinel_instance: Sentinel, namespace: ChainNamespace
) -> None:
    chain = _build_chain(sentinel_instance, namespace, 3)
    chain[1]["title"] = "tampered"
    result = verify_chain(chain)
    assert result.verified is False
    assert result.first_failure_index == 1
    assert "self-check" in result.detail


def test_verify_chain_detects_broken_link(
    sentinel_instance: Sentinel, namespace: ChainNamespace
) -> None:
    chain = _build_chain(sentinel_instance, namespace, 3)
    # Rebuild chain[2]'s attestation_hash so the mangled previous_hash
    # passes self-check. The chain link should still fail.
    from sentinel.core.attestation import _hash_document

    chain[2]["previous_hash"] = "0" * 64
    content = {k: v for k, v in chain[2].items() if k != "attestation_hash"}
    chain[2]["attestation_hash"] = _hash_document(content)

    result = verify_chain(chain)
    assert result.verified is False
    assert result.first_failure_index == 2
    assert "previous_hash mismatch" in result.detail


def test_verify_chain_detects_namespace_drift(
    sentinel_instance: Sentinel,
) -> None:
    ns1 = ChainNamespace("a", "EU", "x")
    ns2 = ChainNamespace("b", "EU", "x")
    a = generate_attestation(sentinel_instance, chain_namespace=ns1)
    b = generate_attestation(sentinel_instance, chain_namespace=ns2)
    result = verify_chain([a, b])
    assert result.verified is False
    assert result.first_failure_index == 1
    assert "chain_namespace drift" in result.detail


def test_verify_chain_empty_is_not_verified() -> None:
    result = verify_chain([])
    assert result.verified is False
    assert result.steps_checked == 0


def test_verify_chain_missing_namespace() -> None:
    bogus = {"schema_version": "1.0.0", "title": "x"}
    result = verify_chain([bogus])
    assert result.verified is False
    assert "no chain_namespace" in result.detail


def test_multiple_namespaces_have_independent_chains(
    sentinel_instance: Sentinel,
) -> None:
    ns1 = ChainNamespace("a", "EU", "x")
    ns2 = ChainNamespace("b", "EU", "y")
    chain1 = _build_chain(sentinel_instance, ns1, 2)
    chain2 = _build_chain(sentinel_instance, ns2, 2)
    assert verify_chain(chain1).verified is True
    assert verify_chain(chain2).verified is True
    # Genesis hashes differ per namespace.
    assert chain1[0]["previous_hash"] != chain2[0]["previous_hash"]


def test_chain_verification_to_dict_roundtrips() -> None:
    result = ChainVerification(verified=True, steps_checked=3, detail="ok")
    d = result.to_dict()
    assert d == {
        "verified": True,
        "steps_checked": 3,
        "detail": "ok",
        "first_failure_index": None,
    }


# ---------------------------------------------------------------------------
# CLI — `sentinel chain verify <file>`
# ---------------------------------------------------------------------------


def _write_chain(path: Path, chain: list[dict]) -> None:
    path.write_text(json.dumps(chain), encoding="utf-8")


def test_cli_chain_verify_passes_for_valid_chain(
    tmp_path: Path,
    sentinel_instance: Sentinel,
    namespace: ChainNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chain = _build_chain(sentinel_instance, namespace, 3)
    pack = tmp_path / "chain.json"
    _write_chain(pack, chain)

    rc = cli.main(["chain", "verify", str(pack)])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert "verified" in captured.out


def test_cli_chain_verify_fails_for_tampered_chain(
    tmp_path: Path,
    sentinel_instance: Sentinel,
    namespace: ChainNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chain = _build_chain(sentinel_instance, namespace, 2)
    chain[0]["title"] = "tampered"
    pack = tmp_path / "chain.json"
    _write_chain(pack, chain)

    rc = cli.main(["chain", "verify", str(pack)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "failed" in captured.out.lower() or "first failure" in captured.out


def test_cli_chain_verify_json_output(
    tmp_path: Path,
    sentinel_instance: Sentinel,
    namespace: ChainNamespace,
    capsys: pytest.CaptureFixture[str],
) -> None:
    chain = _build_chain(sentinel_instance, namespace, 2)
    pack = tmp_path / "chain.json"
    _write_chain(pack, chain)

    rc = cli.main(["chain", "verify", str(pack), "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    payload = json.loads(captured.out)
    assert payload["verified"] is True
    assert payload["steps_checked"] == 2


def test_cli_chain_verify_missing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli.main(["chain", "verify", str(tmp_path / "missing.json")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "not found" in captured.err


def test_cli_chain_verify_invalid_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pack = tmp_path / "bad.json"
    pack.write_text("not json at all", encoding="utf-8")

    rc = cli.main(["chain", "verify", str(pack)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "invalid JSON" in captured.err


def test_cli_chain_verify_rejects_non_list(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pack = tmp_path / "dict.json"
    pack.write_text('{"not": "a list"}', encoding="utf-8")

    rc = cli.main(["chain", "verify", str(pack)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "must be a JSON list" in captured.err


def test_cli_chain_no_subcommand(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli.main(["chain"])
    capsys.readouterr()
    assert rc == 1
