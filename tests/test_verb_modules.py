"""Tests for the canonical v3.4 verb modules.

sentinel.trace, sentinel.attest, sentinel.audit, sentinel.comply
expose the Trace → Attest → Audit → Comply lifecycle as first-class
top-level surfaces. These tests verify each module imports cleanly
and delegates to the underlying primitives without changing
behaviour.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import sentinel as sentinel_pkg
from sentinel import Sentinel, attest, audit, comply, trace
from sentinel.storage import SQLiteStorage
from sentinel.trace import DecisionTrace, PolicyResult


# ---------------------------------------------------------------------------
# Import surface
# ---------------------------------------------------------------------------


def test_canonical_verb_imports_succeed() -> None:
    """`from sentinel import trace, attest, audit, comply` must work."""
    assert trace.__name__ == "sentinel.trace"
    assert attest.__name__ == "sentinel.attest"
    assert audit.__name__ == "sentinel.audit"
    assert comply.__name__ == "sentinel.comply"


def test_verbs_exposed_on_package() -> None:
    """The four verb names must be attributes of the top-level package."""
    assert sentinel_pkg.trace is trace
    assert sentinel_pkg.attest is attest
    assert sentinel_pkg.audit is audit
    assert sentinel_pkg.comply is comply


def test_verbs_in_dunder_all() -> None:
    """The four verbs must appear in sentinel.__all__ for wildcard imports."""
    exported = set(sentinel_pkg.__all__)
    assert {"trace", "attest", "audit", "comply"} <= exported


# ---------------------------------------------------------------------------
# sentinel.trace — re-exports
# ---------------------------------------------------------------------------


def test_trace_module_reexports_primitives() -> None:
    exported = set(trace.__all__)
    assert {
        "Sentinel",
        "DecisionTrace",
        "PolicyResult",
        "DataResidency",
    } <= exported


# ---------------------------------------------------------------------------
# sentinel.attest — generate + verify round-trip
# ---------------------------------------------------------------------------


@pytest.fixture
def sentinel_instance() -> Sentinel:
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="verb-modules-test",
    )


def test_attest_generate_produces_envelope(sentinel_instance: Sentinel) -> None:
    envelope = attest.generate(sentinel_instance, title="unit-test")
    assert envelope["title"] == "unit-test"
    assert envelope["project"] == "verb-modules-test"
    assert len(envelope["attestation_hash"]) == 64


def test_attest_verify_accepts_valid(sentinel_instance: Sentinel) -> None:
    envelope = attest.generate(sentinel_instance, title="unit-test")
    result = attest.verify(envelope)
    assert result.valid is True
    assert result.hash_verified is True


def test_attest_verify_rejects_tampered(sentinel_instance: Sentinel) -> None:
    envelope = attest.generate(sentinel_instance, title="unit-test")
    envelope["title"] = "tampered"
    result = attest.verify(envelope)
    assert result.valid is False
    assert result.what_failed == "hash"


def test_attest_long_form_aliases_preserved() -> None:
    """generate_attestation and verify_attestation remain importable."""
    assert attest.generate_attestation is not None
    assert attest.verify_attestation is not None


# ---------------------------------------------------------------------------
# sentinel.audit — query + verify
# ---------------------------------------------------------------------------


async def _agent_a(ctx: dict) -> dict:  # noqa: RUF029 — async for trace capture
    return {"handled_by": "a"}


async def _agent_b(ctx: dict) -> dict:  # noqa: RUF029
    return {"handled_by": "b"}


def _populate(sentinel_instance: Sentinel) -> None:
    """Produce a handful of traces across a few module-level agents."""
    traced_a = sentinel_instance.trace(_agent_a)
    traced_b = sentinel_instance.trace(_agent_b)

    async def _run() -> None:
        await traced_a({"i": 1})
        await traced_a({"i": 2})
        await traced_b({"i": 3})

    asyncio.run(_run())


def test_audit_query_returns_all_by_default(sentinel_instance: Sentinel) -> None:
    _populate(sentinel_instance)
    traces = audit.query(sentinel_instance)
    assert len(traces) == 3
    for t in traces:
        assert isinstance(t, DecisionTrace)


def test_audit_query_filters_by_agent(sentinel_instance: Sentinel) -> None:
    _populate(sentinel_instance)
    only_a = audit.query(sentinel_instance, agent="_agent_a")
    assert len(only_a) == 2
    assert all(t.agent == "_agent_a" for t in only_a)


def test_audit_query_orders_most_recent_first(sentinel_instance: Sentinel) -> None:
    _populate(sentinel_instance)
    traces = audit.query(sentinel_instance)
    # Most-recent-first ordering — allow for equal timestamps in a
    # tight loop by checking monotonic non-increase.
    for earlier, later in zip(traces, traces[1:]):
        a = earlier.started_at or datetime.min.replace(tzinfo=UTC)
        b = later.started_at or datetime.min.replace(tzinfo=UTC)
        assert a >= b


def test_audit_query_respects_limit(sentinel_instance: Sentinel) -> None:
    _populate(sentinel_instance)
    traces = audit.query(sentinel_instance, limit=1)
    assert len(traces) == 1


def test_audit_query_windows_on_since(sentinel_instance: Sentinel) -> None:
    _populate(sentinel_instance)
    future = datetime.now(UTC) + timedelta(hours=1)
    none_in_future = audit.query(sentinel_instance, since=future)
    assert none_in_future == []


def test_audit_query_windows_on_until(sentinel_instance: Sentinel) -> None:
    _populate(sentinel_instance)
    past = datetime.now(UTC) - timedelta(hours=1)
    none_in_past = audit.query(sentinel_instance, until=past)
    assert none_in_past == []


def test_audit_query_windows_retains_in_range(
    sentinel_instance: Sentinel,
) -> None:
    _populate(sentinel_instance)
    earlier = datetime.now(UTC) - timedelta(hours=1)
    later = datetime.now(UTC) + timedelta(hours=1)
    all_in_range = audit.query(sentinel_instance, since=earlier, until=later)
    assert len(all_in_range) == 3


def test_audit_verify_trace_returns_integrity_result(
    sentinel_instance: Sentinel,
) -> None:
    _populate(sentinel_instance)
    [first, *_] = audit.query(sentinel_instance, limit=1)
    result = audit.verify_trace(sentinel_instance, first.trace_id)
    assert result.found is True
    assert result.verified is True


# ---------------------------------------------------------------------------
# sentinel.comply — export wrapper
# ---------------------------------------------------------------------------


def test_comply_export_writes_pdf(
    tmp_path: Path, sentinel_instance: Sentinel
) -> None:
    pytest.importorskip("reportlab")
    _populate(sentinel_instance)
    out = tmp_path / "evidence.pdf"
    result = comply.export(sentinel_instance, out)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0
    # PDF magic number — '%PDF-' in the first four bytes.
    assert out.read_bytes().startswith(b"%PDF-")


def test_comply_export_accepts_keyword_overrides(
    tmp_path: Path, sentinel_instance: Sentinel
) -> None:
    pytest.importorskip("reportlab")
    _populate(sentinel_instance)
    out = tmp_path / "evidence.pdf"
    result = comply.export(
        sentinel_instance,
        out,
        title="Custom Title",
        max_traces=5,
    )
    assert result == out
    assert out.exists()


def test_comply_export_accepts_explicit_options(
    tmp_path: Path, sentinel_instance: Sentinel
) -> None:
    pytest.importorskip("reportlab")
    _populate(sentinel_instance)
    out = tmp_path / "evidence.pdf"
    options = comply.EvidencePackOptions(title="Q2 audit")
    result = comply.export(sentinel_instance, out, options=options)
    assert result == out
    assert out.exists()


def test_comply_export_rejects_mixed_options(
    tmp_path: Path, sentinel_instance: Sentinel
) -> None:
    pytest.importorskip("reportlab")
    out = tmp_path / "evidence.pdf"
    with pytest.raises(TypeError):
        comply.export(
            sentinel_instance,
            out,
            options=comply.EvidencePackOptions(),
            title="Also a Title",
        )
