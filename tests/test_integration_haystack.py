"""
tests/test_integration_haystack.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for the Haystack integration.

Haystack is mocked at the import level so these tests run without
the optional dep installed. The real integration is invoked with a
mocked haystack module injected into ``sys.modules``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.policy.evaluator import SimpleRuleEvaluator
from sentinel.storage import SQLiteStorage


def _install_fake_haystack() -> None:
    """Install a minimal fake ``haystack`` module so import succeeds."""
    if "haystack" in sys.modules:
        return
    fake = types.ModuleType("haystack")
    fake.__version__ = "2.0.0-fake"  # type: ignore[attr-defined]
    sys.modules["haystack"] = fake


def _remove_fake_haystack() -> None:
    if "haystack" in sys.modules:
        del sys.modules["haystack"]
    # also drop the sentinel.integrations.haystack module so it re-imports
    sys.modules.pop("sentinel.integrations.haystack", None)


def _make_sentinel(tmp_path: Path) -> Sentinel:
    def policy(inputs: dict) -> tuple[bool, str | None]:
        if inputs.get("deny"):
            return False, "blocked_for_test"
        return True, None

    return Sentinel(
        storage=SQLiteStorage(str(tmp_path / "haystack_traces.db")),
        project="haystack-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
        policy_evaluator=SimpleRuleEvaluator({"p.py": policy}),
    )


# ---------------------------------------------------------------------------
# Missing dep
# ---------------------------------------------------------------------------


def test_missing_haystack_raises_helpful_error() -> None:
    _remove_fake_haystack()
    from sentinel.integrations import haystack as haystack_mod

    with pytest.raises(ImportError) as excinfo:
        haystack_mod.SentinelHaystackCallback(sentinel=None)  # type: ignore[arg-type]
    assert "haystack" in str(excinfo.value).lower()
    assert "sentinel-kernel[haystack]" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_component_end_records_trace(tmp_path: Path) -> None:
    _install_fake_haystack()
    # Force re-import so the availability check sees the fake module
    sys.modules.pop("sentinel.integrations.haystack", None)
    from sentinel.integrations.haystack import SentinelHaystackCallback

    sentinel = _make_sentinel(tmp_path)
    cb = SentinelHaystackCallback(sentinel=sentinel)

    cb.on_component_start("retriever", {"query": "What is sovereignty?"})
    cb.on_component_end("retriever", {"documents": ["doc1", "doc2"]})

    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    t = traces[0]
    assert t.agent == "haystack.retriever"
    assert t.model_provider == "haystack"
    assert t.tags["integration"] == "haystack"
    assert t.tags["vendor"] == "deepset"


# ---------------------------------------------------------------------------
# Sovereignty metadata flows from the Sentinel instance
# ---------------------------------------------------------------------------


def test_sovereign_scope_and_residency_from_sentinel(tmp_path: Path) -> None:
    _install_fake_haystack()
    sys.modules.pop("sentinel.integrations.haystack", None)
    from sentinel.integrations.haystack import SentinelHaystackCallback

    sentinel = _make_sentinel(tmp_path)
    cb = SentinelHaystackCallback(sentinel=sentinel)

    cb.on_component_start("reader", {"model": "mistral-7b"})
    cb.on_component_end("reader", {"answer": "Sovereignty is..."})

    trace = sentinel.query(limit=1)[0]
    assert trace.sovereign_scope == "EU"
    assert trace.data_residency == DataResidency.EU_DE
    assert trace.model_name == "mistral-7b"


# ---------------------------------------------------------------------------
# Multiple components
# ---------------------------------------------------------------------------


def test_multiple_components_each_recorded(tmp_path: Path) -> None:
    _install_fake_haystack()
    sys.modules.pop("sentinel.integrations.haystack", None)
    from sentinel.integrations.haystack import SentinelHaystackCallback

    sentinel = _make_sentinel(tmp_path)
    cb = SentinelHaystackCallback(sentinel=sentinel)

    for name in ("retriever", "reader", "reranker"):
        cb.on_component_start(name, {"step": name})
        cb.on_component_end(name, {"ok": True})

    traces = sentinel.query(limit=10)
    assert len(traces) == 3
    agent_names = {t.agent for t in traces}
    assert agent_names == {
        "haystack.retriever",
        "haystack.reader",
        "haystack.reranker",
    }


# ---------------------------------------------------------------------------
# wrap_pipeline_run convenience
# ---------------------------------------------------------------------------


class _FakePipeline:
    def run(self, inputs: dict) -> dict:
        return {"answers": ["42"], "echo": inputs}


def test_wrap_pipeline_run_records_single_trace(tmp_path: Path) -> None:
    _install_fake_haystack()
    sys.modules.pop("sentinel.integrations.haystack", None)
    from sentinel.integrations.haystack import SentinelHaystackCallback

    sentinel = _make_sentinel(tmp_path)
    cb = SentinelHaystackCallback(sentinel=sentinel)

    result = cb.wrap_pipeline_run(_FakePipeline(), inputs={"q": "hi"})

    assert result["answers"] == ["42"]
    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    assert traces[0].agent == "haystack.pipeline"


def test_wrap_pipeline_run_records_trace_on_exception(tmp_path: Path) -> None:
    _install_fake_haystack()
    sys.modules.pop("sentinel.integrations.haystack", None)
    from sentinel.integrations.haystack import SentinelHaystackCallback

    class _BoomPipeline:
        def run(self, inputs: dict) -> dict:  # noqa: ARG002
            raise RuntimeError("kaboom")

    sentinel = _make_sentinel(tmp_path)
    cb = SentinelHaystackCallback(sentinel=sentinel)

    with pytest.raises(RuntimeError):
        cb.wrap_pipeline_run(_BoomPipeline(), inputs={"q": "hi"})

    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    assert "kaboom" in str(traces[0].output)
