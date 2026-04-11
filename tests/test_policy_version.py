"""
tests/test_policy_version.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for PolicyVersion dataclass (Phase 7 — production hardening).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sentinel.policy.evaluator import PolicyVersion


def test_policy_version_from_callable_hashes_source() -> None:
    def my_policy(inputs: dict) -> tuple[bool, str | None]:
        if inputs.get("amount", 0) > 100:
            return False, "too high"
        return True, None

    pv = PolicyVersion.from_callable(my_policy, name="my_policy", version="1.0.0")
    assert pv.name == "my_policy"
    assert pv.version == "1.0.0"
    assert len(pv.hash) == 64  # sha256 hex


def test_policy_version_from_callable_with_unavailable_source() -> None:
    pv = PolicyVersion.from_callable(
        lambda inputs: (True, None),  # noqa: ARG005
        name="lambda-policy",
        version="0.1.0",
    )
    # Should not raise — falls back to repr
    assert pv.name == "lambda-policy"
    assert len(pv.hash) == 64


def test_policy_version_from_callable_builtin_fallback() -> None:
    """Built-in functions have no Python source — exercise the fallback."""
    pv = PolicyVersion.from_callable(len, name="len", version="builtin")
    assert pv.name == "len"
    assert len(pv.hash) == 64


def test_policy_version_from_file(tmp_path: Path) -> None:
    policy_file = tmp_path / "policy.rego"
    policy_file.write_text("package sentinel\nallow = true\n")
    pv = PolicyVersion.from_file(policy_file, version="2026-04-11")
    assert pv.version == "2026-04-11"
    assert pv.name == str(policy_file)
    assert len(pv.hash) == 64


def test_policy_version_as_dict_roundtrip() -> None:
    now = datetime.now()
    later = datetime.now()
    pv = PolicyVersion(
        name="p",
        version="1.0.0",
        hash="a" * 64,
        effective_from=now,
        effective_until=later,
    )
    d = pv.as_dict()
    assert d["name"] == "p"
    assert d["version"] == "1.0.0"
    assert d["hash"] == "a" * 64
    assert d["effective_from"] == now.isoformat()
    assert d["effective_until"] == later.isoformat()


def test_policy_version_as_dict_none_dates() -> None:
    pv = PolicyVersion(name="p", version="1.0.0", hash="x" * 64)
    d = pv.as_dict()
    assert d["effective_from"] is None
    assert d["effective_until"] is None


def test_policy_version_same_source_produces_same_hash() -> None:
    def pa(inputs: dict) -> tuple[bool, str | None]:
        return True, None

    def pb(inputs: dict) -> tuple[bool, str | None]:
        return True, None

    v1 = PolicyVersion.from_callable(pa, name="pa")
    v2 = PolicyVersion.from_callable(pb, name="pb")
    # Different source (different function name) — different hash
    assert v1.hash != v2.hash


def test_policy_version_frozen() -> None:
    import dataclasses

    pv = PolicyVersion(name="p", version="1.0.0", hash="y" * 64)
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        pv.name = "other"  # type: ignore[misc]
