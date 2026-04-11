"""
tests/test_integration_otel.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for OTelExporter without a real OpenTelemetry install.
A fake tracer captures emitted spans so we can assert on attributes.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any

import pytest

from sentinel import DataResidency, Sentinel
from sentinel.integrations.otel import OTelExporter
from sentinel.storage import SQLiteStorage

# ---------------------------------------------------------------------------
# Fake OTel tracer
# ---------------------------------------------------------------------------


class FakeSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attributes: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value


class FakeTracer:
    def __init__(self, *, raise_on_span: bool = False) -> None:
        self.spans: list[FakeSpan] = []
        self.raise_on_span = raise_on_span

    @contextmanager
    def start_as_current_span(self, name: str) -> Any:
        if self.raise_on_span:
            raise ConnectionError("simulated OTLP endpoint unreachable")
        span = FakeSpan(name)
        self.spans.append(span)
        yield span


def _make_sentinel() -> Sentinel:
    return Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="otel-test",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )


def _wait_for_spans(tracer: FakeTracer, count: int, timeout: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    while len(tracer.spans) < count and time.monotonic() < deadline:
        time.sleep(0.01)


def test_otel_span_emitted_on_trace_write() -> None:
    sentinel = _make_sentinel()
    tracer = FakeTracer()
    exporter = OTelExporter(
        sentinel, endpoint="http://fake:4317", tracer_factory=lambda: tracer
    )

    @sentinel.trace
    def do_work(x: int) -> dict[str, int]:
        return {"x": x}

    do_work(7)
    _wait_for_spans(tracer, 1)

    assert len(tracer.spans) == 1
    assert tracer.spans[0].name == "sentinel.decision"
    exporter.shutdown()


def test_otel_span_has_sovereign_scope_attribute() -> None:
    sentinel = _make_sentinel()
    tracer = FakeTracer()
    exporter = OTelExporter(
        sentinel, endpoint="http://fake:4317", tracer_factory=lambda: tracer
    )

    @sentinel.trace
    def do_work() -> dict[str, int]:
        return {"ok": 1}

    do_work()
    _wait_for_spans(tracer, 1)

    attrs = tracer.spans[0].attributes
    assert attrs["sentinel.sovereign_scope"] == "EU"
    assert attrs["sentinel.data_residency"] == "EU-DE"
    assert attrs["sentinel.schema_version"] == "1.0.0"
    exporter.shutdown()


def test_otel_span_has_policy_result_attribute() -> None:
    sentinel = _make_sentinel()
    tracer = FakeTracer()
    exporter = OTelExporter(
        sentinel, endpoint="http://fake:4317", tracer_factory=lambda: tracer
    )

    @sentinel.trace
    def do_work() -> dict[str, int]:
        return {"ok": 1}

    do_work()
    _wait_for_spans(tracer, 1)

    attrs = tracer.spans[0].attributes
    # NullPolicyEvaluator returns NOT_EVALUATED but only if @trace has a policy
    # path. With no policy the trace has no policy_evaluation, so the attribute
    # is the default.
    assert attrs["sentinel.policy_result"] == "NOT_EVALUATED"
    assert "sentinel.trace_id" in attrs
    assert attrs["sentinel.agent"].endswith("do_work")
    exporter.shutdown()


def test_otel_export_fails_silently_on_connection_error(caplog: pytest.LogCaptureFixture) -> None:
    """A failing span export must not crash the decision path."""
    sentinel = _make_sentinel()
    tracer = FakeTracer(raise_on_span=True)
    exporter = OTelExporter(
        sentinel, endpoint="http://fake:4317", tracer_factory=lambda: tracer
    )

    @sentinel.trace
    def do_work() -> dict[str, int]:
        return {"ok": 1}

    # Must not raise
    result = do_work()
    assert result == {"ok": 1}

    # Give worker thread a moment to swallow the error
    time.sleep(0.1)

    # Trace was still written to storage
    traces = sentinel.query(limit=10)
    assert len(traces) == 1
    exporter.shutdown()


def test_otel_missing_dep_helpful_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """If opentelemetry-sdk is not installed, the error names the pip extra."""
    import sentinel.integrations.otel as otel_mod

    def fake_import() -> tuple[Any, Any, Any]:
        raise ImportError(otel_mod._MISSING_DEP_MESSAGE)

    monkeypatch.setattr(otel_mod, "_import_otel", fake_import)

    sentinel = _make_sentinel()
    with pytest.raises(ImportError, match="sentinel-kernel\\[otel\\]"):
        OTelExporter(sentinel, endpoint="http://fake:4317")
