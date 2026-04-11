"""Tests for sentinel.core.budget.BudgetTracker."""

from __future__ import annotations

import math

import pytest

from sentinel import BudgetTracker, Sentinel
from sentinel.storage import SQLiteStorage


@pytest.fixture
def sentinel() -> Sentinel:
    return Sentinel(storage=SQLiteStorage(":memory:"), project="budget-test")


def test_check_allows_within_budget(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=10.0)
    result = budget.check(estimated_cost=0.25)
    assert result.allowed is True
    assert result.remaining == 10.0
    assert result.reason is None


def test_check_blocks_over_budget(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=1.0)
    result = budget.check(estimated_cost=2.0)
    assert result.allowed is False
    assert result.reason == "budget_exhausted"


def test_check_blocks_negative_cost(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=5.0)
    result = budget.check(estimated_cost=-1.0)
    assert result.allowed is False
    assert result.reason == "invalid_cost"


def test_check_blocks_nan(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=5.0)
    result = budget.check(estimated_cost=math.nan)
    assert result.allowed is False
    assert result.reason == "invalid_cost"


def test_check_blocks_inf(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=5.0)
    result = budget.check(estimated_cost=math.inf)
    assert result.allowed is False
    assert result.reason == "invalid_cost"


def test_record_creates_trace(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=10.0)
    trace = budget.record("api:mistral", actual_cost=0.23)
    assert trace.trace_id
    assert trace.tags["kind"] == "budget"
    # Stored
    retrieved = sentinel.storage.get(trace.trace_id)
    assert retrieved is not None
    assert retrieved.output["cost"] == 0.23


def test_record_updates_cumulative_spend(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=10.0)
    budget.record("api:a", actual_cost=1.0)
    budget.record("api:b", actual_cost=2.5)
    assert budget.spend == pytest.approx(3.5)
    assert budget.remaining == pytest.approx(6.5)


def test_record_rejects_invalid(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=10.0)
    with pytest.raises(ValueError):
        budget.record("api:x", actual_cost=-1)
    with pytest.raises(ValueError):
        budget.record("api:x", actual_cost=math.nan)


def test_status_accurate(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=50.0, currency="EUR")
    budget.record("a", 5.0)
    budget.record("b", 7.5)
    status = budget.status()
    assert status["limit"] == 50.0
    assert status["currency"] == "EUR"
    assert status["spend"] == pytest.approx(12.5)
    assert status["remaining"] == pytest.approx(37.5)
    assert status["trace_count"] == 2
    assert len(status["trace_ids"]) == 2


def test_limit_must_be_non_negative(sentinel: Sentinel) -> None:
    with pytest.raises(ValueError):
        BudgetTracker(sentinel=sentinel, limit=-1)


def test_record_with_context(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=10.0)
    trace = budget.record(
        "api:openai",
        actual_cost=1.25,
        context={"model": "gpt-4", "tokens": 1200},
    )
    retrieved = sentinel.storage.get(trace.trace_id)
    assert retrieved is not None
    assert retrieved.output["context"]["model"] == "gpt-4"


def test_properties_expose_state(sentinel: Sentinel) -> None:
    budget = BudgetTracker(sentinel=sentinel, limit=12.0, currency="EUR")
    assert budget.limit == 12.0
    assert budget.currency == "EUR"
    assert budget.spend == 0.0
    assert budget.remaining == 12.0


def test_budget_airgap(sentinel: Sentinel, monkeypatch: pytest.MonkeyPatch) -> None:
    """BudgetTracker must work with no network calls."""
    import socket

    def no_network(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("network call attempted")

    monkeypatch.setattr(socket.socket, "connect", no_network)

    budget = BudgetTracker(sentinel=sentinel, limit=10.0)
    assert budget.check(1.0).allowed
    trace = budget.record("offline", 1.0)
    assert trace.trace_id
