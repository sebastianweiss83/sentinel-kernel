"""Tests for sentinel.integrations.crewai with a mocked crewai package."""

from __future__ import annotations

import sys
import types

import pytest

from sentinel import Sentinel
from sentinel.storage import SQLiteStorage


@pytest.fixture
def mocked_crewai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a stub ``crewai`` module so the integration imports cleanly."""
    stub = types.ModuleType("crewai")
    monkeypatch.setitem(sys.modules, "crewai", stub)
    # Re-import the integration module under the stubbed crewai.
    for name in list(sys.modules):
        if name.startswith("sentinel.integrations.crewai"):
            monkeypatch.delitem(sys.modules, name, raising=False)


def test_crewai_records_trace_on_task_completion(
    mocked_crewai: None,
) -> None:
    from sentinel.integrations.crewai import SentinelCrewCallback

    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="crew-test")
    cb = SentinelCrewCallback(sentinel=sentinel)

    cb.task_callback({"result": "classified"})
    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    assert traces[0].tags["integration"] == "crewai"
    assert traces[0].agent == "crewai_task"


def test_crewai_serialises_non_dict_output(mocked_crewai: None) -> None:
    from sentinel.integrations.crewai import SentinelCrewCallback

    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="crew-test")
    cb = SentinelCrewCallback(sentinel=sentinel)
    cb.task_callback("plain-string-output")
    traces = sentinel.query(limit=1)
    assert traces[0].output["type"] == "str"


def test_crewai_missing_dep_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no crewai module installed, instantiation must raise ImportError."""
    # Ensure the module re-imports with _HAS_CREWAI = False.
    monkeypatch.setitem(sys.modules, "crewai", None)
    for name in list(sys.modules):
        if name == "sentinel.integrations.crewai":
            monkeypatch.delitem(sys.modules, name, raising=False)

    from sentinel.integrations import crewai as module

    module._HAS_CREWAI = False
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="crew-test")
    with pytest.raises(ImportError, match="sentinel-kernel\\[crewai\\]"):
        module.SentinelCrewCallback(sentinel=sentinel)
