"""Tests for Sentinel.verify_output and DecisionTrace.verify_output."""

from __future__ import annotations

import pytest

from sentinel import Sentinel
from sentinel.storage import SQLiteStorage


@pytest.fixture
def sentinel() -> Sentinel:
    return Sentinel(storage=SQLiteStorage(":memory:"), project="verify-out-test")


def _trace_a_call(sentinel: Sentinel) -> str:
    @sentinel.trace
    def act(payload: dict) -> dict:
        return {"decision": "approved", "amount": payload["amount"]}

    act(payload={"amount": 100})
    traces = sentinel.query(limit=1)
    return traces[0].trace_id


def test_verify_matching_output(sentinel: Sentinel) -> None:
    trace_id = _trace_a_call(sentinel)
    result = sentinel.verify_output(
        trace_id,
        {"decision": "approved", "amount": 100},
    )
    assert result.verified is True
    assert result.match is True


def test_verify_tampered_output_fails(sentinel: Sentinel) -> None:
    trace_id = _trace_a_call(sentinel)
    result = sentinel.verify_output(
        trace_id,
        {"decision": "approved", "amount": 999},
    )
    assert result.verified is False
    assert result.match is False


def test_verify_missing_trace(sentinel: Sentinel) -> None:
    result = sentinel.verify_output("nonexistent-trace", {"foo": "bar"})
    assert result.verified is False
    assert result.detail == "trace not found"


def test_verify_output_non_dict(sentinel: Sentinel) -> None:
    trace_id = _trace_a_call(sentinel)
    result = sentinel.verify_output(trace_id, "not-a-dict")  # type: ignore[arg-type]
    assert result.verified is False
    assert "dict" in result.detail


def test_trace_verify_output_method(sentinel: Sentinel) -> None:
    trace_id = _trace_a_call(sentinel)
    trace = sentinel.storage.get(trace_id)
    assert trace is not None
    assert trace.verify_output({"decision": "approved", "amount": 100}) is True
    assert trace.verify_output({"decision": "approved", "amount": 0}) is False


def test_verify_output_result_to_dict(sentinel: Sentinel) -> None:
    trace_id = _trace_a_call(sentinel)
    d = sentinel.verify_output(
        trace_id, {"decision": "approved", "amount": 100}
    ).to_dict()
    assert set(d.keys()) == {"verified", "trace_id", "stored_hash", "computed_hash", "match", "detail"}


def test_verify_output_no_hash_recorded(sentinel: Sentinel) -> None:
    from sentinel.core.trace import DecisionTrace

    trace = DecisionTrace(project="t", agent="manual")
    # output stays empty → output_hash stays None
    sentinel.storage.save(trace)
    result = sentinel.verify_output(trace.trace_id, {"x": 1})
    assert result.verified is False
    assert result.stored_hash is None
    assert "no output_hash" in result.detail


def test_trace_verify_output_no_hash() -> None:
    from sentinel.core.trace import DecisionTrace

    trace = DecisionTrace(project="t", agent="manual")
    assert trace.verify_output({"x": 1}) is False


def test_trace_verify_output_non_dict() -> None:
    from sentinel.core.trace import DecisionTrace

    trace = DecisionTrace(project="t", agent="manual", output={"a": 1})
    assert trace.verify_output("string-not-dict") is False  # type: ignore[arg-type]


def test_verify_airgap(sentinel: Sentinel, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    monkeypatch.setattr(
        socket.socket,
        "connect",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("net")),
    )
    trace_id = _trace_a_call(sentinel)
    assert sentinel.verify_output(
        trace_id,
        {"decision": "approved", "amount": 100},
    ).verified
