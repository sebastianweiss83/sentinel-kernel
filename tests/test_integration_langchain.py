"""
tests/test_integration_langchain.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for SentinelCallbackHandler without a real langchain-core install.

We inject a fake ``langchain_core.callbacks`` module into sys.modules
before importing the integration, so the handler can subclass a real
BaseCallbackHandler type.
"""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any
from uuid import uuid4

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.storage import SQLiteStorage

# ---------------------------------------------------------------------------
# Fake langchain-core module
# ---------------------------------------------------------------------------


class _FakeBaseCallbackHandler:
    """Stand-in for langchain_core.callbacks.BaseCallbackHandler."""


def _install_fake_langchain() -> None:
    pkg = types.ModuleType("langchain_core")
    callbacks = types.ModuleType("langchain_core.callbacks")
    callbacks.BaseCallbackHandler = _FakeBaseCallbackHandler  # type: ignore[attr-defined]
    pkg.callbacks = callbacks  # type: ignore[attr-defined]
    sys.modules["langchain_core"] = pkg
    sys.modules["langchain_core.callbacks"] = callbacks


def _uninstall_fake_langchain() -> None:
    for name in ("langchain_core.callbacks", "langchain_core"):
        sys.modules.pop(name, None)


@pytest.fixture
def fake_langchain(monkeypatch: pytest.MonkeyPatch) -> Any:
    _install_fake_langchain()
    # Reload the integration so it picks up the fake base class
    import sentinel.integrations.langchain as lc_mod  # noqa: PLC0415

    importlib.reload(lc_mod)
    yield lc_mod
    _uninstall_fake_langchain()
    importlib.reload(lc_mod)


def _make_sentinel() -> Sentinel:
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="lc-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )


class _FakeGeneration:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeLLMResult:
    def __init__(self, texts: list[str]) -> None:
        self.generations = [[_FakeGeneration(t) for t in texts]]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_callback_handler_records_trace_on_llm_end(fake_langchain: Any) -> None:
    sentinel = _make_sentinel()
    handler = fake_langchain.SentinelCallbackHandler(sentinel=sentinel)

    run_id = uuid4()
    handler.on_llm_start(
        serialized={"name": "mistral-large-2"},
        prompts=["What is 2+2?"],
        run_id=run_id,
    )
    handler.on_llm_end(_FakeLLMResult(["4"]), run_id=run_id)

    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    assert traces[0].agent == "langchain.llm"
    assert traces[0].output == {"generations": ["4"]}


def test_callback_handler_records_model_name(fake_langchain: Any) -> None:
    sentinel = _make_sentinel()
    handler = fake_langchain.SentinelCallbackHandler(sentinel=sentinel)

    run_id = uuid4()
    handler.on_llm_start(
        serialized={"name": "claude-opus-4-6"},
        prompts=["hi"],
        run_id=run_id,
    )
    handler.on_llm_end(_FakeLLMResult(["hello"]), run_id=run_id)

    traces = sentinel.query(limit=10)
    assert traces[0].model_name == "claude-opus-4-6"
    assert traces[0].model_provider == "langchain"


def test_callback_handler_records_latency(fake_langchain: Any) -> None:
    import time

    sentinel = _make_sentinel()
    handler = fake_langchain.SentinelCallbackHandler(sentinel=sentinel)

    run_id = uuid4()
    handler.on_llm_start(serialized={"name": "m"}, prompts=["x"], run_id=run_id)
    time.sleep(0.01)
    handler.on_llm_end(_FakeLLMResult(["y"]), run_id=run_id)

    traces = sentinel.query(limit=10)
    assert traces[0].latency_ms is not None
    assert traces[0].latency_ms >= 0


def test_callback_handler_uses_sentinel_storage(fake_langchain: Any) -> None:
    """Traces go to the Sentinel instance's storage, with its sovereignty metadata."""
    sentinel = _make_sentinel()
    handler = fake_langchain.SentinelCallbackHandler(sentinel=sentinel)

    handler.on_llm_start(
        serialized={"name": "m"}, prompts=["p"], run_id=uuid4()
    )
    handler.on_llm_end(_FakeLLMResult(["r"]))  # no run_id: uses singleton key

    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    t = traces[0]
    assert t.data_residency == DataResidency.EU_DE
    assert t.sovereign_scope == "EU"
    assert t.storage_backend == "sqlite"
    assert t.tags.get("integration") == "langchain"


def test_callback_handler_missing_dep_helpful_error() -> None:
    """When langchain-core is not installed, instantiation points at the extra."""
    _uninstall_fake_langchain()
    import sentinel.integrations.langchain as lc_mod  # noqa: PLC0415

    importlib.reload(lc_mod)

    sentinel = _make_sentinel()
    with pytest.raises(ImportError, match="sentinel-kernel\\[langchain\\]"):
        lc_mod.SentinelCallbackHandler(sentinel=sentinel)


def test_callback_handler_records_chain_end(fake_langchain: Any) -> None:
    sentinel = _make_sentinel()
    handler = fake_langchain.SentinelCallbackHandler(sentinel=sentinel)

    run_id = uuid4()
    handler.on_chain_start(
        serialized={"name": "procurement_chain"},
        inputs={"amount": 5000},
        run_id=run_id,
    )
    handler.on_chain_end({"decision": "approved"}, run_id=run_id)

    traces = sentinel.query(agent="langchain.chain", limit=10)
    assert len(traces) == 1
    assert traces[0].output == {"decision": "approved"}
