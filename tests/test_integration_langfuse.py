"""
tests/test_integration_langfuse.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for LangFuseEnricher with a fake langfuse client.
"""

from __future__ import annotations

from typing import Any

import pytest

from sentinel import DataResidency, PolicyResult, Sentinel
from sentinel.core.trace import PolicyEvaluation
from sentinel.integrations.langfuse import LangFuseEnricher
from sentinel.storage import SQLiteStorage


class FakeLangfuseClient:
    """Minimal stand-in for langfuse.Langfuse with update_trace()."""

    def __init__(self) -> None:
        self.updates: list[dict[str, Any]] = []

    def update_trace(self, trace_id: str, metadata: dict[str, Any]) -> None:
        self.updates.append({"trace_id": trace_id, "metadata": metadata})


def _make_sentinel_with_trace(policy_result: PolicyResult = PolicyResult.ALLOW) -> tuple[Sentinel, str]:
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="lf-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )

    @sentinel.trace
    def decide(x: int) -> dict[str, int]:
        return {"x": x}

    decide(1)
    traces = sentinel.query(limit=1)
    trace = traces[0]
    # Stamp a policy eval so the enricher has something to attach
    trace.policy_evaluation = PolicyEvaluation(
        policy_id="policies/approve.py",
        policy_version="v1",
        result=policy_result,
        rule_triggered=None if policy_result == PolicyResult.ALLOW else "over_cap",
    )
    sentinel.storage.save(trace := _rebuild_trace(trace, sentinel, policy_result))
    return sentinel, trace.trace_id


def _rebuild_trace(original: Any, sentinel: Sentinel, policy_result: PolicyResult) -> Any:
    """Return a new DecisionTrace with the same id and a policy eval."""
    from sentinel.core.trace import DecisionTrace, PolicyEvaluation

    new = DecisionTrace(
        trace_id=original.trace_id + "-enriched",
        project=original.project,
        agent=original.agent,
        inputs=original.inputs,
        data_residency=original.data_residency,
        sovereign_scope=original.sovereign_scope,
        storage_backend=original.storage_backend,
    )
    new.policy_evaluation = PolicyEvaluation(
        policy_id="policies/approve.py",
        policy_version="v1",
        result=policy_result,
        rule_triggered=None if policy_result == PolicyResult.ALLOW else "over_cap",
    )
    new.complete(output={"result": "ok"}, latency_ms=1)
    return new


def test_langfuse_enrichment_adds_sovereignty_metadata() -> None:
    sentinel, sentinel_trace_id = _make_sentinel_with_trace()
    client = FakeLangfuseClient()
    enricher = LangFuseEnricher(sentinel, client=client)

    metadata = enricher.enrich(
        langfuse_trace_id="lf_abc123",
        sentinel_trace_id=sentinel_trace_id,
    )

    assert metadata["sentinel.sovereign_scope"] == "EU"
    assert metadata["sentinel.data_residency"] == "EU-DE"
    assert metadata["sentinel.schema_version"] == "1.0.0"
    assert metadata["sentinel.trace_id"] == sentinel_trace_id
    assert metadata["sentinel.policy"] == "policies/approve.py"
    assert metadata["sentinel.policy_result"] == "ALLOW"

    assert len(client.updates) == 1
    assert client.updates[0]["trace_id"] == "lf_abc123"
    assert client.updates[0]["metadata"] == metadata


def test_langfuse_enrichment_includes_deny_rule() -> None:
    sentinel, trace_id = _make_sentinel_with_trace(policy_result=PolicyResult.DENY)
    enricher = LangFuseEnricher(sentinel, client=FakeLangfuseClient())

    metadata = enricher.enrich(langfuse_trace_id="lf_deny", sentinel_trace_id=trace_id)
    assert metadata["sentinel.policy_result"] == "DENY"
    assert metadata["sentinel.policy_rule"] == "over_cap"


def test_langfuse_join_key_is_trace_id() -> None:
    sentinel, trace_id = _make_sentinel_with_trace()
    enricher = LangFuseEnricher(sentinel, client=FakeLangfuseClient())
    assert enricher.join_key(trace_id) == trace_id


def test_langfuse_enricher_raises_for_unknown_trace() -> None:
    sentinel, _ = _make_sentinel_with_trace()
    enricher = LangFuseEnricher(sentinel, client=FakeLangfuseClient())
    with pytest.raises(KeyError, match="Sentinel trace not found"):
        enricher.enrich(langfuse_trace_id="lf_x", sentinel_trace_id="does-not-exist")


def test_langfuse_missing_dep_helpful_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import sentinel.integrations.langfuse as lf_mod

    def fake_import() -> Any:
        raise ImportError(lf_mod._MISSING_DEP_MESSAGE)

    monkeypatch.setattr(lf_mod, "_import_langfuse_client", fake_import)
    sentinel, _ = _make_sentinel_with_trace()
    with pytest.raises(ImportError, match="sentinel-kernel\\[langfuse\\]"):
        LangFuseEnricher(sentinel)  # no client injected → real import attempted


def test_langfuse_enricher_supports_legacy_trace_method() -> None:
    """Older langfuse SDK exposes .trace(id=, metadata=) — still works."""
    class LegacyClient:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def trace(self, id: str, metadata: dict[str, Any]) -> None:
            self.calls.append({"id": id, "metadata": metadata})

    sentinel, trace_id = _make_sentinel_with_trace()
    client = LegacyClient()
    enricher = LangFuseEnricher(sentinel, client=client)
    enricher.enrich(langfuse_trace_id="lf_legacy", sentinel_trace_id=trace_id)

    assert len(client.calls) == 1
    assert client.calls[0]["id"] == "lf_legacy"
    assert "sentinel.sovereign_scope" in client.calls[0]["metadata"]
