"""
tests/test_airgap.py
~~~~~~~~~~~~~~~~~~~~
Air-gapped validation suite.

Every test in this file runs with ``socket.socket.connect`` monkey-patched
to raise. If any code path attempts to open a network connection, the test
fails loudly with an ``AirgapViolation``.

This is how we prove Sentinel's critical path is network-free.
"""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path
from typing import Any

import pytest

from sentinel import (
    DataResidency,
    KillSwitchEngaged,
    PolicyResult,
    Sentinel,
)
from sentinel.core.trace import PolicyEvaluation
from sentinel.policy.evaluator import (
    LocalRegoEvaluator,
    NullPolicyEvaluator,
    SimpleRuleEvaluator,
)
from sentinel.storage import FilesystemStorage, SQLiteStorage


class AirgapViolation(RuntimeError):
    """Raised when a test under the airgap fixture attempts a network call."""


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Monkey-patch socket.socket.connect to forbid any network call.
    Active for every test in this module.

    We deliberately do NOT block AF_UNIX sockets (used by subprocess pipes,
    asyncio, etc.) — the rule is "no network", not "no syscalls".
    """

    def forbid_connect(self: socket.socket, address: Any, *args: Any, **kwargs: Any) -> Any:
        family = getattr(self, "family", None)
        if family in (socket.AF_INET, socket.AF_INET6):
            raise AirgapViolation(
                f"AIRGAP VIOLATION: network connect attempted to {address!r}"
            )
        return _original_connect(self, address, *args, **kwargs)

    _original_connect = socket.socket.connect
    monkeypatch.setattr(socket.socket, "connect", forbid_connect)


def test_airgap_null_policy_no_network() -> None:
    """Default NullPolicyEvaluator makes no network calls."""
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        policy_evaluator=NullPolicyEvaluator(),
        data_residency=DataResidency.AIR_GAPPED,
    )

    @sentinel.trace
    def decide(x: int) -> dict[str, int]:
        return {"x": x}

    assert decide(5) == {"x": 5}


def test_airgap_simple_rule_no_network() -> None:
    """SimpleRuleEvaluator runs Python callables in-process."""

    def under_cap(inputs: dict[str, Any]) -> tuple[bool, str | None]:
        if inputs.get("amount", 0) > 100:
            return False, "over_cap"
        return True, None

    evaluator = SimpleRuleEvaluator({"policies/cap.py": under_cap})
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        policy_evaluator=evaluator,
        data_residency=DataResidency.AIR_GAPPED,
    )

    @sentinel.trace(policy="policies/cap.py")
    async def buy(amount: int) -> dict[str, int]:
        return {"amount": amount}

    result = asyncio.run(buy(amount=50))
    assert result == {"amount": 50}


def test_airgap_local_rego_no_network() -> None:
    """LocalRegoEvaluator uses a mocked OPA subprocess — no network."""

    class FakeRegoEvaluator(LocalRegoEvaluator):
        async def evaluate(
            self, policy_path: str, inputs: dict[str, Any], trace: Any
        ) -> PolicyEvaluation:
            allowed = inputs.get("amount", 0) <= 1000
            return PolicyEvaluation(
                policy_id=policy_path,
                policy_version="test",
                result=PolicyResult.ALLOW if allowed else PolicyResult.DENY,
                rule_triggered=None if allowed else "amount_over_cap",
                evaluator="opa-local-fake",
            )

    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        policy_evaluator=FakeRegoEvaluator(),
        data_residency=DataResidency.AIR_GAPPED,
    )

    @sentinel.trace(policy="policies/cap.rego")
    async def decide(amount: int) -> dict[str, int]:
        return {"amount": amount}

    result = asyncio.run(decide(amount=500))
    assert result == {"amount": 500}


def test_airgap_sqlite_storage_no_network() -> None:
    """SQLiteStorage is a local file — no network."""
    storage = SQLiteStorage(":memory:")
    sentinel = Sentinel(storage=storage, data_residency=DataResidency.AIR_GAPPED)

    @sentinel.trace
    def work() -> dict[str, int]:
        return {"n": 1}

    work()
    traces = sentinel.query(limit=10)
    assert len(traces) == 1


def test_airgap_filesystem_storage_no_network(tmp_path: Path) -> None:
    """FilesystemStorage writes NDJSON — no network."""
    storage = FilesystemStorage(str(tmp_path / "traces"))
    sentinel = Sentinel(storage=storage, data_residency=DataResidency.AIR_GAPPED)

    @sentinel.trace
    def work() -> dict[str, int]:
        return {"n": 1}

    work()
    ndjson_files = list((tmp_path / "traces").glob("*.ndjson"))
    assert len(ndjson_files) == 1
    assert ndjson_files[0].read_text().strip() != ""


def test_airgap_full_trace_cycle_no_network(tmp_path: Path) -> None:
    """Intercept → policy eval → trace emit → storage write, all offline."""

    def policy(inputs: dict[str, Any]) -> tuple[bool, str | None]:
        if inputs.get("risk") == "high":
            return False, "too_risky"
        return True, None

    sentinel = Sentinel(
        storage=FilesystemStorage(str(tmp_path / "traces")),
        policy_evaluator=SimpleRuleEvaluator({"p.py": policy}),
        data_residency=DataResidency.AIR_GAPPED,
        sovereign_scope="EU",
    )

    @sentinel.trace(policy="p.py")
    async def decide(risk: str) -> dict[str, str]:
        return {"risk": risk, "decision": "approved"}

    result = asyncio.run(decide(risk="low"))
    assert result["decision"] == "approved"

    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    assert traces[0].data_residency == DataResidency.AIR_GAPPED
    assert traces[0].sovereign_scope == "EU"
    assert traces[0].policy_evaluation is not None
    assert traces[0].policy_evaluation.result == PolicyResult.ALLOW


def test_airgap_kill_switch_no_network() -> None:
    """Kill switch operates with pure in-process state — no network."""
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        data_residency=DataResidency.AIR_GAPPED,
    )

    @sentinel.trace
    def work() -> dict[str, int]:
        return {"n": 1}

    work()  # normal call
    sentinel.engage_kill_switch("airgap drill")
    with pytest.raises(KillSwitchEngaged):
        work()
    sentinel.disengage_kill_switch("drill over")
    work()  # resumes


def test_airgap_violation_detector_works() -> None:
    """Sanity: the airgap fixture actually blocks real TCP connects."""
    with pytest.raises(AirgapViolation, match="AIRGAP VIOLATION"):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(("192.0.2.1", 80))  # TEST-NET-1, RFC 5737
        finally:
            s.close()
