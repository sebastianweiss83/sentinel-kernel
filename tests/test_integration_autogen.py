"""Tests for sentinel.integrations.autogen with a mocked autogen package."""

from __future__ import annotations

import sys
import types

import pytest

from sentinel import Sentinel
from sentinel.storage import SQLiteStorage


@pytest.fixture
def mocked_autogen(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = types.ModuleType("autogen")
    monkeypatch.setitem(sys.modules, "autogen", stub)
    for name in list(sys.modules):
        if name.startswith("sentinel.integrations.autogen"):
            monkeypatch.delitem(sys.modules, name, raising=False)


class _FakeAgent:
    def __init__(self) -> None:
        self.name = "fake"

    def generate_reply(self, messages=None, **kwargs):  # noqa: ANN001
        return {"reply": "ok", "count": len(messages or [])}


def test_autogen_wraps_generate_reply(mocked_autogen: None) -> None:
    from sentinel.integrations.autogen import SentinelAutoGenHook

    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="ag")
    hook = SentinelAutoGenHook(sentinel=sentinel)
    agent = _FakeAgent()
    hook.register(agent)

    reply = agent.generate_reply(messages=[{"role": "user", "content": "hi"}])
    assert reply["reply"] == "ok"

    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    assert traces[0].tags["integration"] == "autogen"
    assert traces[0].agent == "autogen:fake"


def test_autogen_register_requires_method(mocked_autogen: None) -> None:
    from sentinel.integrations.autogen import SentinelAutoGenHook

    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="ag")
    hook = SentinelAutoGenHook(sentinel=sentinel)

    class _NoReply:
        pass

    with pytest.raises(AttributeError):
        hook.register(_NoReply())


def test_autogen_missing_dep_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "autogen", None)
    for name in list(sys.modules):
        if name == "sentinel.integrations.autogen":
            monkeypatch.delitem(sys.modules, name, raising=False)

    from sentinel.integrations import autogen as module

    module._HAS_AUTOGEN = False
    sentinel = Sentinel(storage=SQLiteStorage(":memory:"), project="ag")
    with pytest.raises(ImportError, match="sentinel-kernel\\[autogen\\]"):
        module.SentinelAutoGenHook(sentinel=sentinel)
