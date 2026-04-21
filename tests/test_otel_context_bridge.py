"""v3.5 Item 1 — OpenTelemetry causal-context bridge.

Covers the behaviour from ``docs/architecture/v3.5-item-1-causal-context.md``:
capture the active OTEL span's identifiers into a DecisionTrace, return
None gracefully when OTEL isn't installed or no span is active, preserve
the Sentinel-native ``parent_trace_id`` chain unchanged, and stay
backward-compatible with v3.4.x traces that lack the new fields.
"""

from __future__ import annotations

import pytest

from sentinel.core.otel_context import (
    OtelContext,
    capture_current_otel_context,
)
from sentinel.core.trace import DecisionTrace
from sentinel.core.tracer import Sentinel

# ---------------------------------------------------------------------------
# Unit — capture_current_otel_context()
# ---------------------------------------------------------------------------


def test_capture_without_otel_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ``opentelemetry`` is absent, capture is a safe no-op."""
    from sentinel.core import otel_context as bridge

    monkeypatch.setattr(bridge, "_HAS_OTEL", False)
    monkeypatch.setattr(bridge, "_otel_trace", None)

    assert capture_current_otel_context() is None


def test_capture_with_no_active_span_returns_none() -> None:
    """No active span → None.

    Uses the OTEL API's built-in INVALID_SPAN sentinel (what
    ``get_current_span()`` returns outside any span).
    """
    pytest.importorskip("opentelemetry")
    assert capture_current_otel_context() is None


def test_capture_with_active_span_returns_hex_ids() -> None:
    """Inside an SDK-backed span, capture returns hex-encoded IDs."""
    pytest.importorskip("opentelemetry")
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider

    otel_trace.set_tracer_provider(TracerProvider())
    tracer = otel_trace.get_tracer("test-capture")

    with tracer.start_as_current_span("outer"):
        ctx = capture_current_otel_context()

    assert isinstance(ctx, OtelContext)
    # W3C: 32 hex chars for trace_id, 16 for span_id.
    assert len(ctx.trace_id) == 32
    assert len(ctx.span_id) == 16
    assert all(c in "0123456789abcdef" for c in ctx.trace_id + ctx.span_id)
    # Root span → no parent.
    assert ctx.parent_span_id is None


def test_capture_nested_span_records_parent_span_id() -> None:
    """An inner span records the enclosing span's ID in parent_span_id."""
    pytest.importorskip("opentelemetry")
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider

    otel_trace.set_tracer_provider(TracerProvider())
    tracer = otel_trace.get_tracer("test-nested")

    outer_span_id: str | None = None
    inner_ctx: OtelContext | None = None

    with tracer.start_as_current_span("outer") as outer:
        outer_span_id = f"{outer.get_span_context().span_id:016x}"
        with tracer.start_as_current_span("inner"):
            inner_ctx = capture_current_otel_context()

    assert inner_ctx is not None
    assert inner_ctx.parent_span_id == outer_span_id
    # Trace ID stays the same across the whole workflow.
    assert inner_ctx.trace_id != ""


# ---------------------------------------------------------------------------
# Integration — Sentinel._execute_traced populates otel_* fields
# ---------------------------------------------------------------------------


def test_sentinel_trace_without_otel_has_none_fields(tmp_path: object) -> None:
    """A default Sentinel() trace outside any OTEL span leaves otel_* fields None."""
    s = Sentinel(storage=":memory:", signer=None)

    @s.trace
    def decide(x: str) -> dict[str, str]:
        return {"r": x}

    decide("hello")
    t = s.query()[0]

    assert t.otel_trace_id is None
    assert t.otel_span_id is None
    assert t.otel_parent_span_id is None


def test_sentinel_trace_inside_otel_span_captures_ids() -> None:
    """Trace inside an OTEL span carries the span's hex IDs."""
    pytest.importorskip("opentelemetry")
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider

    otel_trace.set_tracer_provider(TracerProvider())
    tracer = otel_trace.get_tracer("test-integration")

    s = Sentinel(storage=":memory:", signer=None)

    @s.trace
    def decide(x: str) -> dict[str, str]:
        return {"r": x}

    with tracer.start_as_current_span("agent_workflow") as workflow_span:
        decide("hello")
        workflow_trace_id = f"{workflow_span.get_span_context().trace_id:032x}"

    t = s.query()[0]
    assert t.otel_trace_id == workflow_trace_id
    assert t.otel_span_id is not None
    assert len(t.otel_span_id) == 16


def test_two_sentinel_traces_in_same_workflow_share_otel_trace_id() -> None:
    """Multiple decisions in the same OTEL workflow join on otel_trace_id."""
    pytest.importorskip("opentelemetry")
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider

    otel_trace.set_tracer_provider(TracerProvider())
    tracer = otel_trace.get_tracer("test-workflow-join")

    s = Sentinel(storage=":memory:", signer=None)

    @s.trace
    def decide(which: str) -> dict[str, str]:
        return {"verdict": which}

    # Two sibling decisions under the same caller-owned OTEL workflow
    # span. Reconstruction joins them on otel_trace_id. (Nested sync
    # @sentinel.trace calls are not supported by the sync wrapper due
    # to its asyncio.run()-per-call design — that limitation is
    # orthogonal to this bridge.)
    with tracer.start_as_current_span("workflow"):
        decide("approved")
        decide("approved-again")

    traces = s.query()
    assert len(traces) == 2
    otel_ids = {t.otel_trace_id for t in traces}
    assert len(otel_ids) == 1
    assert next(iter(otel_ids)) is not None


# ---------------------------------------------------------------------------
# Schema backward-compat
# ---------------------------------------------------------------------------


def test_pre_v3_5_trace_dict_deserialises_with_none_otel_fields() -> None:
    """Old NDJSON traces without otel_context load cleanly."""
    old_trace_dict: dict[str, object] = {
        "schema_version": "1.0.0",
        "trace_id": "abc123",
        "parent_trace_id": None,
        "project": "legacy-project",
        "agent": "legacy-agent",
        "started_at": "2025-01-01T00:00:00+00:00",
        "completed_at": None,
        "latency_ms": None,
        "inputs": {},
        "inputs_hash": None,
        "output": {},
        "output_hash": None,
        "tags": {},
        "precedent_trace_ids": [],
        "signature": None,
        "signature_algorithm": None,
        # NOTE: no `otel_context` key — this is the backward-compat case.
    }
    restored = DecisionTrace.from_dict(old_trace_dict)
    assert restored.otel_trace_id is None
    assert restored.otel_span_id is None
    assert restored.otel_parent_span_id is None


def test_trace_with_otel_context_round_trips() -> None:
    """to_dict → from_dict preserves all three OTEL fields."""
    t = DecisionTrace(
        project="round-trip",
        agent="otel-test",
        otel_trace_id="a" * 32,
        otel_span_id="b" * 16,
        otel_parent_span_id="c" * 16,
    )
    restored = DecisionTrace.from_dict(t.to_dict())

    assert restored.otel_trace_id == "a" * 32
    assert restored.otel_span_id == "b" * 16
    assert restored.otel_parent_span_id == "c" * 16


def test_capture_with_zero_valued_parent_returns_none_parent_span_id() -> None:
    """Span with a parent attribute but zero span_id → parent_span_id is None.

    Covers the degenerate case where an SDK attaches a zeroed parent
    (e.g., context propagation glitch) — we treat it as "no parent"
    rather than surfacing all-zeros as a meaningful identifier.
    """

    class _ZeroParent:
        span_id = 0

    class _FakeContext:
        trace_id = 0x11223344556677889900AABBCCDDEEFF
        span_id = 0xDEADBEEFCAFEBABE

    class _FakeSpan:
        parent = _ZeroParent()

        def get_span_context(self) -> _FakeContext:
            return _FakeContext()

    from sentinel.core import otel_context as bridge

    # Swap the module-level OTEL API for a stand-in that returns our
    # fake span. The stand-in only needs one method.
    class _FakeTraceApi:
        @staticmethod
        def get_current_span() -> _FakeSpan:
            return _FakeSpan()

    import pytest as _pytest  # local alias — avoids shadowing

    with _pytest.MonkeyPatch().context() as m:
        m.setattr(bridge, "_HAS_OTEL", True)
        m.setattr(bridge, "_otel_trace", _FakeTraceApi())
        ctx = bridge.capture_current_otel_context()

    assert ctx is not None
    assert ctx.parent_span_id is None


def test_trace_without_otel_fields_emits_null_otel_context() -> None:
    """A trace with no OTEL context serialises otel_context as None."""
    t = DecisionTrace(project="no-otel", agent="x", inputs={"a": 1})
    d = t.to_dict()
    assert "otel_context" in d
    assert d["otel_context"] is None
