"""Tests for Sentinel.preflight() — advisory checks with no trace written."""

from __future__ import annotations

import pytest

from sentinel import Sentinel
from sentinel.core.trace import PolicyEvaluation, PolicyResult
from sentinel.policy.evaluator import PolicyEvaluator
from sentinel.storage import SQLiteStorage


class _AllowAll(PolicyEvaluator):
    async def evaluate(self, *, policy_path, inputs, trace):
        return PolicyEvaluation(
            policy_id=policy_path,
            policy_version="1",
            result=PolicyResult.ALLOW,
        )


class _DenyAll(PolicyEvaluator):
    async def evaluate(self, *, policy_path, inputs, trace):
        return PolicyEvaluation(
            policy_id=policy_path,
            policy_version="1",
            result=PolicyResult.DENY,
            rule_triggered="blanket_deny",
        )


@pytest.fixture
def sentinel() -> Sentinel:
    return Sentinel(storage=SQLiteStorage(":memory:"), project="preflight-test")


def test_preflight_cleared_no_policy(sentinel: Sentinel) -> None:
    result = sentinel.preflight("action:do")
    assert result.cleared is True
    assert result.policy_result == "NOT_EVALUATED"
    assert result.reasons == []


def test_preflight_blocked_by_kill_switch(sentinel: Sentinel) -> None:
    sentinel.engage_kill_switch("maintenance")
    result = sentinel.preflight("action:any")
    assert result.cleared is False
    assert result.kill_switch_active is True
    assert result.policy_result == "DENY"
    assert any("kill_switch" in r for r in result.reasons)


def test_preflight_blocked_by_policy_deny() -> None:
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="pf",
        policy_evaluator=_DenyAll(),
    )
    result = sentinel.preflight("action:x")
    assert result.cleared is False
    assert result.policy_result == "DENY"
    assert result.reasons and result.reasons[0].startswith("policy:")


def test_preflight_allowed_by_policy() -> None:
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="pf",
        policy_evaluator=_AllowAll(),
    )
    result = sentinel.preflight("action:x")
    assert result.cleared is True
    assert result.policy_result == "ALLOW"


def test_preflight_writes_no_trace(sentinel: Sentinel) -> None:
    before = sentinel.query(limit=1000)
    sentinel.preflight("action:do")
    after = sentinel.query(limit=1000)
    assert len(after) == len(before)


class _Exploding(PolicyEvaluator):
    async def evaluate(self, *, policy_path, inputs, trace):
        raise RuntimeError("boom")


class _Exception(PolicyEvaluator):
    async def evaluate(self, *, policy_path, inputs, trace):
        return PolicyEvaluation(
            policy_id=policy_path,
            policy_version="1",
            result=PolicyResult.EXCEPTION,
        )


def test_preflight_evaluator_error_returns_deny() -> None:
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="pf",
        policy_evaluator=_Exploding(),
    )
    result = sentinel.preflight("action:x")
    assert result.cleared is False
    assert result.reasons and result.reasons[0].startswith("evaluator_error:")


def test_preflight_other_result_not_cleared() -> None:
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="pf",
        policy_evaluator=_Exception(),
    )
    result = sentinel.preflight("action:x")
    assert result.cleared is False
    assert result.policy_result.endswith("EXCEPTION")


def test_preflight_to_dict(sentinel: Sentinel) -> None:
    d = sentinel.preflight("action:y").to_dict()
    assert set(d.keys()) == {"cleared", "kill_switch_active", "policy_result", "reasons"}


def test_preflight_airgap(sentinel: Sentinel, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    monkeypatch.setattr(
        socket.socket,
        "connect",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("net")),
    )
    result = sentinel.preflight("action:offline")
    assert result.cleared is True
