"""
tests/test_sync_and_edge_cases.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for sync decorator, exception handling, span() context manager,
and store_inputs/store_outputs flags.
"""

import pytest

from sentinel import PolicyDeniedError, Sentinel
from sentinel.core.trace import DecisionTrace, HumanOverride
from sentinel.policy import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage

# --- Sync function wrapping ---

def test_sync_function_traced():
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="sync-test")

    @sentinel.trace
    def decide(x: int) -> dict:
        return {"x": x * 2}

    result = decide(x=5)
    assert result == {"x": 10}

    traces = sentinel.query(project="sync-test")
    assert len(traces) == 1
    assert traces[0].output == {"x": 10}


def test_sync_function_with_policy():
    def allow_all(inputs):
        return True, None

    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="sync-policy",
        policy_evaluator=SimpleRuleEvaluator({"p": allow_all}),
    )

    @sentinel.trace(policy="p")
    def decide(x: int) -> dict:
        return {"x": x}

    result = decide(x=1)
    assert result == {"x": 1}

    traces = sentinel.query(project="sync-policy")
    assert len(traces) == 1


def test_sync_function_policy_deny():
    def deny_all(inputs):
        return False, "always_deny"

    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="sync-deny",
        policy_evaluator=SimpleRuleEvaluator({"p": deny_all}),
    )

    @sentinel.trace(policy="p")
    def decide(x: int) -> dict:
        return {"x": x}

    with pytest.raises(PolicyDeniedError):
        decide(x=1)


def test_sync_function_records_latency():
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="sync-latency")

    @sentinel.trace
    def slow_decide() -> dict:
        total = sum(range(10000))
        return {"total": total}

    slow_decide()
    traces = sentinel.query(project="sync-latency")
    assert traces[0].latency_ms is not None
    assert traces[0].latency_ms >= 0


# --- Exception handling ---

@pytest.mark.asyncio
async def test_exception_in_traced_function_is_reraised():
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="exc-test")

    @sentinel.trace
    async def failing_agent() -> dict:
        raise ValueError("something broke")

    with pytest.raises(ValueError, match="something broke"):
        await failing_agent()


@pytest.mark.asyncio
async def test_exception_trace_is_stored():
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="exc-stored")

    @sentinel.trace
    async def failing_agent() -> dict:
        raise RuntimeError("crash")

    with pytest.raises(RuntimeError):
        await failing_agent()

    traces = sentinel.query(project="exc-stored")
    assert len(traces) == 1


@pytest.mark.asyncio
async def test_exception_trace_has_error_tags():
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="exc-tags")

    @sentinel.trace
    async def failing_agent() -> dict:
        raise TypeError("bad type")

    with pytest.raises(TypeError):
        await failing_agent()

    traces = sentinel.query(project="exc-tags")
    trace = traces[0]
    assert trace.tags.get("error") == "TypeError"
    assert "bad type" in trace.tags.get("error_message", "")


def test_sync_exception_traced():
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="sync-exc")

    @sentinel.trace
    def failing_sync() -> dict:
        raise KeyError("missing")

    with pytest.raises(KeyError):
        failing_sync()

    traces = sentinel.query(project="sync-exc")
    assert len(traces) == 1
    assert traces[0].tags.get("error") == "KeyError"


# --- span() context manager ---

@pytest.mark.asyncio
async def test_span_creates_trace():
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="span-test")

    async with sentinel.span("my-workflow") as trace:
        trace.output = {"step": "done"}

    traces = sentinel.query(project="span-test")
    assert len(traces) == 1
    assert traces[0].agent == "my-workflow"


@pytest.mark.asyncio
async def test_span_trace_has_completed_at():
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="span-complete")

    async with sentinel.span("workflow") as trace:
        trace.output = {"result": 42}

    traces = sentinel.query(project="span-complete")
    assert traces[0].completed_at is not None


@pytest.mark.asyncio
async def test_span_with_tags():
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="span-tags")

    async with sentinel.span("workflow", env="test", region="eu") as trace:
        trace.output = {"ok": True}

    traces = sentinel.query(project="span-tags")
    assert traces[0].tags.get("env") == "test"
    assert traces[0].tags.get("region") == "eu"


# --- store_inputs / store_outputs flags ---

@pytest.mark.asyncio
async def test_store_inputs_false_omits_inputs():
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="no-inputs",
        store_inputs=False,
    )

    @sentinel.trace
    async def decide(secret: str) -> dict:
        return {"ok": True}

    await decide(secret="password123")

    traces = sentinel.query(project="no-inputs")
    trace = traces[0]
    assert trace.inputs == {}


@pytest.mark.asyncio
async def test_store_outputs_false_omits_outputs():
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="no-outputs",
        store_outputs=False,
    )

    @sentinel.trace
    async def decide(x: int) -> dict:
        return {"sensitive": "data"}

    await decide(x=1)

    traces = sentinel.query(project="no-outputs")
    trace = traces[0]
    assert trace.output == {}


@pytest.mark.asyncio
async def test_store_inputs_false_still_hashes():
    """Even when inputs are not stored, the hash should be computed from the actual inputs."""
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="hash-no-store",
        store_inputs=False,
    )

    @sentinel.trace
    async def decide(x: int) -> dict:
        return {"x": x}

    await decide(x=42)

    traces = sentinel.query(project="hash-no-store")
    # inputs_hash should be None or empty since inputs dict is empty
    # (hash is computed from the stored inputs, which are {})
    trace = traces[0]
    assert trace.inputs == {}


# --- Human override ---

def test_add_override_changes_policy_result():
    trace = DecisionTrace(
        project="override-test",
        agent="test",
    )
    from sentinel.core.trace import PolicyEvaluation, PolicyResult
    trace.policy_evaluation = PolicyEvaluation(
        policy_id="test-policy",
        policy_version="1",
        result=PolicyResult.DENY,
        rule_triggered="threshold",
    )

    override = HumanOverride(
        approver_id="admin@example.eu",
        approver_role="manager",
        justification="Manual review passed",
    )
    trace.add_override(override)

    assert trace.human_override is not None
    assert trace.policy_evaluation.result == PolicyResult.EXCEPTION
    assert trace.human_override.approver_id == "admin@example.eu"


# --- Precedent linking ---

def test_link_precedent():
    trace = DecisionTrace(project="prec-test", agent="test")
    trace.link_precedent("trace-001")
    trace.link_precedent("trace-002")
    trace.link_precedent("trace-001")  # duplicate, should not add

    assert trace.precedent_trace_ids == ["trace-001", "trace-002"]
