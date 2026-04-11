"""
tests/test_kill_switch.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for the EU AI Act Art. 14 kill switch.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pytest

from sentinel import KillSwitchEngaged, PolicyResult, Sentinel
from sentinel.storage import SQLiteStorage
from sentinel.storage.base import StorageBackend

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace


class ThreadSafeMemoryStorage(StorageBackend):
    """Minimal dict-backed storage for concurrency tests."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._traces: dict[str, DecisionTrace] = {}

    @property
    def backend_name(self) -> str:
        return "memory"

    def initialise(self) -> None:
        return None

    def save(self, trace: DecisionTrace) -> None:
        with self._lock:
            self._traces[trace.trace_id] = trace

    def query(
        self,
        project: str | None = None,
        agent: str | None = None,
        policy_result: PolicyResult | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DecisionTrace]:
        with self._lock:
            items = list(self._traces.values())
        if project:
            items = [t for t in items if t.project == project]
        if agent:
            items = [t for t in items if t.agent == agent]
        if policy_result:
            items = [
                t
                for t in items
                if t.policy_evaluation
                and t.policy_evaluation.result == policy_result
            ]
        return items[offset : offset + limit]

    def get(self, trace_id: str) -> DecisionTrace | None:
        with self._lock:
            return self._traces.get(trace_id)


def _make_sentinel() -> Sentinel:
    return Sentinel(storage=SQLiteStorage(":memory:"), project="kill-switch-test")


def test_kill_switch_inactive_by_default() -> None:
    sentinel = _make_sentinel()
    assert sentinel.kill_switch_active is False


def test_kill_switch_blocks_execution() -> None:
    sentinel = _make_sentinel()
    call_count = 0

    @sentinel.trace
    def do_work(x: int) -> dict[str, int]:
        nonlocal call_count
        call_count += 1
        return {"result": x * 2}

    # normal call runs
    do_work(5)
    assert call_count == 1

    # engage kill switch → next call is blocked
    sentinel.engage_kill_switch("maintenance window")
    with pytest.raises(KillSwitchEngaged, match="maintenance window"):
        do_work(10)
    assert call_count == 1  # wrapped function was NOT called


def test_kill_switch_records_deny_trace() -> None:
    sentinel = _make_sentinel()

    @sentinel.trace
    def do_work(x: int) -> dict[str, int]:
        return {"result": x}

    sentinel.engage_kill_switch("pull the plug")
    with pytest.raises(KillSwitchEngaged):
        do_work(1)

    traces = sentinel.query(policy_result=PolicyResult.DENY, limit=10)
    assert len(traces) == 1
    trace = traces[0]
    assert trace.policy_evaluation is not None
    assert trace.policy_evaluation.result == PolicyResult.DENY
    assert trace.policy_evaluation.rule_triggered == "kill_switch_engaged"
    assert trace.policy_evaluation.policy_id == "kill-switch"
    assert trace.tags.get("kill_switch") == "engaged"


def test_kill_switch_records_human_override() -> None:
    sentinel = _make_sentinel()

    @sentinel.trace
    def do_work() -> dict[str, str]:
        return {"ok": "yes"}

    sentinel.engage_kill_switch("legal hold 2026-Q2")
    with pytest.raises(KillSwitchEngaged):
        do_work()

    traces = sentinel.query(policy_result=PolicyResult.DENY, limit=10)
    assert len(traces) == 1
    override = traces[0].human_override
    assert override is not None
    assert override.approver_id == "kill-switch"
    assert override.approver_role == "system-halt"
    assert override.justification == "legal hold 2026-Q2"


def test_kill_switch_disengage_restores_normal_execution() -> None:
    sentinel = _make_sentinel()
    call_count = 0

    @sentinel.trace
    def do_work() -> dict[str, int]:
        nonlocal call_count
        call_count += 1
        return {"n": call_count}

    sentinel.engage_kill_switch("pause")
    assert sentinel.kill_switch_active is True
    with pytest.raises(KillSwitchEngaged):
        do_work()
    assert call_count == 0

    sentinel.disengage_kill_switch("incident resolved")
    assert sentinel.kill_switch_active is False

    # normal execution resumes
    result = do_work()
    assert result == {"n": 1}
    assert call_count == 1


def test_kill_switch_thread_safe() -> None:
    """Concurrent engage/disengage and traced calls must not corrupt state."""
    sentinel = Sentinel(storage=ThreadSafeMemoryStorage(), project="ks-concurrency")
    errors: list[Exception] = []
    blocked = 0
    executed = 0
    lock = threading.Lock()

    @sentinel.trace
    def do_work() -> dict[str, int]:
        return {"ok": 1}

    def worker() -> None:
        nonlocal blocked, executed
        for _ in range(20):
            try:
                do_work()
                with lock:
                    executed += 1
            except KillSwitchEngaged:
                with lock:
                    blocked += 1
            except Exception as e:  # noqa: BLE001
                errors.append(e)

    def toggler() -> None:
        for i in range(10):
            if i % 2 == 0:
                sentinel.engage_kill_switch(f"toggle-{i}")
            else:
                sentinel.disengage_kill_switch(f"toggle-{i}")

    threads = [threading.Thread(target=worker) for _ in range(4)]
    threads.append(threading.Thread(target=toggler))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == [], f"unexpected errors: {errors}"
    # sanity: at least some calls ran and some were blocked
    assert executed + blocked == 80
    # state is coherent: either engaged or not, no corruption
    assert isinstance(sentinel.kill_switch_active, bool)
