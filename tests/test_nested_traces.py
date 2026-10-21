"""
tests/test_nested_traces.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Nested and mixed sync/async ``@sentinel.trace`` calls.

Regression tests for the v3.5.0 yank: a sync traced function called
from inside another traced function (or from async code) raised
``RuntimeError: asyncio.run() cannot be called from a running event
loop``. Agent-calls-agent is the core multi-agent pattern, so every
nesting shape must produce one complete trace per call.
"""

from __future__ import annotations

import asyncio
import contextvars
import socket
from pathlib import Path

import pytest

from sentinel import PolicyDeniedError, PolicyResult, Sentinel
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="unset"
)


def _sentinel(tmp_path: Path, **kwargs: object) -> Sentinel:
    return Sentinel(storage=SQLiteStorage(str(tmp_path / "traces.db")), **kwargs)


def test_sync_inside_sync(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def inner() -> dict:
        return {"verdict": "approved"}

    @sentinel.trace
    def outer() -> dict:
        return inner()

    assert outer() == {"verdict": "approved"}
    traces = sentinel.query(limit=10)
    assert len(traces) == 2
    assert all(t.completed_at is not None for t in traces)
    assert {"inner", "outer"} <= {t.agent.split(".")[-1] for t in traces}


def test_three_levels_deep(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def level3() -> dict:
        return {"depth": 3}

    @sentinel.trace
    def level2() -> dict:
        return level3()

    @sentinel.trace
    def level1() -> dict:
        return level2()

    assert level1() == {"depth": 3}
    assert len(sentinel.query(limit=10)) == 3


def test_sync_inside_async_traced(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def sync_step() -> dict:
        return {"step": "sync"}

    @sentinel.trace
    async def async_agent() -> dict:
        return sync_step()

    assert asyncio.run(async_agent()) == {"step": "sync"}
    assert len(sentinel.query(limit=10)) == 2


def test_sync_traced_called_from_plain_async_code(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def decide() -> dict:
        return {"ok": True}

    async def application() -> dict:
        return decide()

    assert asyncio.run(application()) == {"ok": True}
    assert len(sentinel.query(limit=10)) == 1


def test_inner_exception_propagates_and_both_traces_saved(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def inner() -> dict:
        raise ValueError("inner failure")

    @sentinel.trace
    def outer() -> dict:
        return inner()

    with pytest.raises(ValueError, match="inner failure"):
        outer()

    traces = sentinel.query(limit=10)
    assert len(traces) == 2
    assert all(t.tags.get("error") == "ValueError" for t in traces)


def test_nested_policy_deny_records_rule(tmp_path: Path) -> None:
    def deny_all(_inputs: dict) -> tuple[bool, str | None]:
        return False, "nested_denied"

    sentinel = _sentinel(
        tmp_path,
        policy_evaluator=SimpleRuleEvaluator({"policies/deny.py": deny_all}),
    )

    @sentinel.trace(policy="policies/deny.py")
    def inner() -> dict:
        return {"never": "reached"}

    @sentinel.trace
    def outer() -> dict:
        return inner()

    with pytest.raises(PolicyDeniedError):
        outer()

    denied = sentinel.query(policy_result=PolicyResult.DENY, limit=10)
    assert len(denied) == 1
    assert denied[0].policy_evaluation is not None
    assert denied[0].policy_evaluation.rule_triggered == "nested_denied"


def test_contextvars_visible_in_nested_sync_trace(tmp_path: Path) -> None:
    """Context such as an active OTEL span must reach the inner call."""
    sentinel = _sentinel(tmp_path)
    seen: list[str] = []

    @sentinel.trace
    def inner() -> dict:
        seen.append(_request_id.get())
        return {}

    @sentinel.trace
    def outer() -> dict:
        _request_id.set("req-42")
        return inner()

    outer()
    assert seen == ["req-42"]


def test_nested_traces_signed_by_default(tmp_path: Path) -> None:
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def inner() -> dict:
        return {}

    @sentinel.trace
    def outer() -> dict:
        return inner()

    outer()
    traces = sentinel.query(limit=10)
    if sentinel._signer is None:  # pragma: no cover - signing disabled in env
        pytest.skip("no default signer configured")
    assert all(t.signature for t in traces)
    assert all(t.signature_algorithm == "Ed25519" for t in traces)


def test_preflight_inside_running_loop(tmp_path: Path) -> None:
    def allow_all(_inputs: dict) -> tuple[bool, str | None]:
        return True, None

    sentinel = _sentinel(
        tmp_path,
        policy_evaluator=SimpleRuleEvaluator({"refund": allow_all}),
    )

    async def application() -> str:
        return sentinel.preflight("refund").policy_result

    assert asyncio.run(application()) == "ALLOW"


def test_nested_traces_work_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_network(*_args: object, **_kwargs: object) -> None:
        raise OSError("network disabled in test")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    sentinel = _sentinel(tmp_path)

    @sentinel.trace
    def inner() -> dict:
        return {}

    @sentinel.trace
    def outer() -> dict:
        return inner()

    outer()
    assert len(sentinel.query(limit=10)) == 2


def test_nested_trace_with_opentelemetry_span(tmp_path: Path) -> None:
    """The exact scenario that failed on a fresh v3.5.0 install."""
    trace_api = pytest.importorskip("opentelemetry.trace")
    sdk = pytest.importorskip("opentelemetry.sdk.trace")

    tracer = sdk.TracerProvider().get_tracer("test")
    sentinel = _sentinel(tmp_path)
    span_ids: list[int] = []

    @sentinel.trace
    def inner() -> dict:
        span_ids.append(trace_api.get_current_span().get_span_context().span_id)
        return {"v": "approved"}

    @sentinel.trace
    def outer() -> dict:
        return inner()

    with tracer.start_as_current_span("agent_flow") as span:
        assert outer() == {"v": "approved"}
        expected = span.get_span_context().span_id

    assert span_ids == [expected]
    assert len(sentinel.query(limit=10)) == 2
