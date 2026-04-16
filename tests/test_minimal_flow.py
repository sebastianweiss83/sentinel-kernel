"""
tests/test_minimal_flow.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for the full Sentinel decorator flow end to end.

Covers: trace storage, query, agent name, project, output, latency.
"""

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.storage import SQLiteStorage


@pytest.fixture
def sentinel_instance():
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="flow-test",
        data_residency=DataResidency.LOCAL,
    )


@pytest.mark.asyncio
async def test_trace_decorator_stores_trace(sentinel_instance):
    @sentinel_instance.trace
    async def simple_decision(x: int) -> dict:
        return {"doubled": x * 2}

    await simple_decision(5)

    traces = sentinel_instance.query(project="flow-test")
    assert len(traces) == 1


@pytest.mark.asyncio
async def test_query_returns_traces(sentinel_instance):
    @sentinel_instance.trace
    async def decision_a(val: str) -> dict:
        return {"val": val}

    await decision_a("alpha")
    await decision_a("beta")

    traces = sentinel_instance.query(project="flow-test")
    assert len(traces) == 2


@pytest.mark.asyncio
async def test_trace_has_correct_agent_name(sentinel_instance):
    @sentinel_instance.trace
    async def my_named_agent(x: int) -> dict:
        return {"x": x}

    await my_named_agent(1)

    traces = sentinel_instance.query(project="flow-test")
    assert len(traces) == 1
    # Agent name is set from function __qualname__
    assert "my_named_agent" in traces[0].agent


@pytest.mark.asyncio
async def test_trace_has_correct_project(sentinel_instance):
    @sentinel_instance.trace
    async def project_checker() -> dict:
        return {"ok": True}

    await project_checker()

    traces = sentinel_instance.query(project="flow-test")
    assert traces[0].project == "flow-test"


@pytest.mark.asyncio
async def test_trace_records_output_hash(sentinel_instance):
    """Hash-only default: trace records output_hash, not raw output."""
    @sentinel_instance.trace
    async def output_fn(n: int) -> dict:
        return {"square": n * n}

    await output_fn(7)

    traces = sentinel_instance.query(project="flow-test")
    assert traces[0].output == {}  # privacy default
    assert traces[0].output_hash is not None
    assert len(traces[0].output_hash) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_trace_records_raw_output_when_opted_in():
    """Explicit opt-in: store_outputs=True preserves the raw output."""
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="opt-in-test",
        data_residency=DataResidency.LOCAL,
        store_outputs=True,
    )

    @sentinel.trace
    async def output_fn(n: int) -> dict:
        return {"square": n * n}

    await output_fn(7)

    traces = sentinel.query(project="opt-in-test")
    assert traces[0].output == {"square": 49}
    assert traces[0].output_hash is not None


@pytest.mark.asyncio
async def test_trace_records_nonnegative_latency_ms(sentinel_instance):
    @sentinel_instance.trace
    async def fast_fn() -> dict:
        return {"done": True}

    await fast_fn()

    traces = sentinel_instance.query(project="flow-test")
    assert traces[0].latency_ms is not None
    assert traces[0].latency_ms >= 0


@pytest.mark.asyncio
async def test_trace_with_tags(sentinel_instance):
    @sentinel_instance.trace(tags={"env": "test", "version": "v1"})
    async def tagged_fn() -> dict:
        return {"tagged": True}

    await tagged_fn()

    traces = sentinel_instance.query(project="flow-test")
    assert traces[0].tags["env"] == "test"
    assert traces[0].tags["version"] == "v1"


@pytest.mark.asyncio
async def test_trace_id_is_unique_per_call(sentinel_instance):
    @sentinel_instance.trace
    async def repeated_fn() -> dict:
        return {"called": True}

    await repeated_fn()
    await repeated_fn()

    traces = sentinel_instance.query(project="flow-test")
    ids = [t.trace_id for t in traces]
    assert len(set(ids)) == 2


@pytest.mark.asyncio
async def test_non_dict_return_is_wrapped():
    """Non-dict returns are wrapped as {'result': repr(value)} before
    hashing. Uses store_outputs=True so the wrapped payload is visible."""
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="wrap-test",
        data_residency=DataResidency.LOCAL,
        store_outputs=True,
    )

    @sentinel.trace
    async def returns_string() -> str:
        return "hello"

    await returns_string()

    traces = sentinel.query(project="wrap-test")
    assert "result" in traces[0].output


@pytest.mark.asyncio
async def test_custom_agent_name_via_decorator_arg(sentinel_instance):
    @sentinel_instance.trace(agent_name="custom-agent-name")
    async def fn_with_custom_name() -> dict:
        return {"ok": True}

    await fn_with_custom_name()

    traces = sentinel_instance.query(project="flow-test")
    assert traces[0].agent == "custom-agent-name"
