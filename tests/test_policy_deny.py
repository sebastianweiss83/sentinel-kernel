"""
tests/test_policy_deny.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for policy denial behaviour.

Covers: PolicyDeniedError raised on DENY, denied trace stored,
denial trace has DENY result and rule_triggered set in persisted payload.

Note: DecisionTrace.from_dict() does not currently reconstruct
policy_evaluation. Tests verify policy data via:
  - storage.query(policy_result=...) — uses the indexed column
  - raw payload from storage.get() — reads persisted JSON
"""

import json

import pytest

from sentinel import DataResidency, PolicyDeniedError, PolicyResult, Sentinel
from sentinel.policy import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


def _make_sentinel(rule_fn, policy_name: str = "test/policy"):
    storage = SQLiteStorage(":memory:")
    evaluator = SimpleRuleEvaluator({policy_name: rule_fn})
    s = Sentinel(
        storage=storage,
        project="policy-test",
        data_residency=DataResidency.LOCAL,
        policy_evaluator=evaluator,
    )
    return s, storage, policy_name


@pytest.mark.asyncio
async def test_simple_rule_evaluator_deny_raises_policy_denied_error():
    def always_deny(inputs: dict) -> tuple[bool, str | None]:
        return False, "always_blocked"

    sentinel, storage, policy_name = _make_sentinel(always_deny)

    @sentinel.trace(policy=policy_name)
    async def guarded_fn() -> dict:
        return {"should": "not reach here"}

    with pytest.raises(PolicyDeniedError):
        await guarded_fn()


@pytest.mark.asyncio
async def test_denial_trace_is_stored():
    def deny_large_amounts(inputs: dict) -> tuple[bool, str | None]:
        if inputs.get("amount", 0) > 1000:
            return False, "amount_exceeds_limit"
        return True, None

    sentinel, storage, policy_name = _make_sentinel(deny_large_amounts)

    @sentinel.trace(policy=policy_name)
    async def process_payment(amount: int) -> dict:
        return {"processed": amount}

    with pytest.raises(PolicyDeniedError):
        await process_payment(amount=5000)

    traces = sentinel.query(project="policy-test")
    assert len(traces) == 1


@pytest.mark.asyncio
async def test_denial_trace_has_policy_result_deny():
    def deny_always(inputs: dict) -> tuple[bool, str | None]:
        return False, "blocked_by_rule"

    sentinel, storage, policy_name = _make_sentinel(deny_always)

    @sentinel.trace(policy=policy_name)
    async def fn() -> dict:
        return {"ok": True}

    with pytest.raises(PolicyDeniedError):
        await fn()

    # Verify via indexed policy_result column filter
    deny_traces = storage.query(policy_result=PolicyResult.DENY)
    assert len(deny_traces) == 1

    # Verify policy details in the persisted payload
    trace_id = deny_traces[0].trace_id
    raw_row = storage._connection().execute(
        "SELECT payload FROM decision_traces WHERE trace_id = ?", (trace_id,)
    ).fetchone()
    payload = json.loads(raw_row["payload"])
    assert payload["policy"]["result"] == "DENY"


@pytest.mark.asyncio
async def test_denial_trace_has_rule_triggered_set():
    def deny_with_named_rule(inputs: dict) -> tuple[bool, str | None]:
        return False, "specific_rule_name"

    sentinel, storage, policy_name = _make_sentinel(deny_with_named_rule)

    @sentinel.trace(policy=policy_name)
    async def fn() -> dict:
        return {"ok": True}

    with pytest.raises(PolicyDeniedError):
        await fn()

    traces = sentinel.query(project="policy-test")
    trace_id = traces[0].trace_id
    raw_row = storage._connection().execute(
        "SELECT payload FROM decision_traces WHERE trace_id = ?", (trace_id,)
    ).fetchone()
    payload = json.loads(raw_row["payload"])
    assert payload["policy"]["rule_triggered"] == "specific_rule_name"


@pytest.mark.asyncio
async def test_allow_does_not_raise():
    def allow_small_amounts(inputs: dict) -> tuple[bool, str | None]:
        if inputs.get("amount", 0) > 1000:
            return False, "amount_exceeds_limit"
        return True, None

    sentinel, storage, policy_name = _make_sentinel(allow_small_amounts)

    @sentinel.trace(policy=policy_name)
    async def process_payment(amount: int) -> dict:
        return {"processed": amount}

    result = await process_payment(amount=100)
    assert result["processed"] == 100

    allow_traces = storage.query(policy_result=PolicyResult.ALLOW)
    assert len(allow_traces) == 1

    trace_id = allow_traces[0].trace_id
    raw_row = storage._connection().execute(
        "SELECT payload FROM decision_traces WHERE trace_id = ?", (trace_id,)
    ).fetchone()
    payload = json.loads(raw_row["payload"])
    assert payload["policy"]["result"] == "ALLOW"


@pytest.mark.asyncio
async def test_mixed_allow_and_deny_both_stored():
    def threshold_rule(inputs: dict) -> tuple[bool, str | None]:
        if inputs.get("amount", 0) > 500:
            return False, "over_threshold"
        return True, None

    sentinel, storage, policy_name = _make_sentinel(threshold_rule)

    @sentinel.trace(policy=policy_name)
    async def payment(amount: int) -> dict:
        return {"amount": amount}

    await payment(amount=100)

    with pytest.raises(PolicyDeniedError):
        await payment(amount=1000)

    all_traces = sentinel.query(project="policy-test")
    assert len(all_traces) == 2

    assert len(storage.query(policy_result=PolicyResult.ALLOW)) == 1
    assert len(storage.query(policy_result=PolicyResult.DENY)) == 1


@pytest.mark.asyncio
async def test_policy_denied_error_message_contains_trace_id():
    def deny_fn(inputs: dict) -> tuple[bool, str | None]:
        return False, "test_rule"

    sentinel, storage, policy_name = _make_sentinel(deny_fn)

    @sentinel.trace(policy=policy_name)
    async def fn() -> dict:
        return {}

    with pytest.raises(PolicyDeniedError) as exc_info:
        await fn()

    traces = sentinel.query(project="policy-test")
    assert traces[0].trace_id in str(exc_info.value)
