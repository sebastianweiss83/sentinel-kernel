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


# ---------------------------------------------------------------------------
# Wrapper delegation — initialise, get, backend_name
# ---------------------------------------------------------------------------


def test_otel_wrapper_delegates_initialise_and_get() -> None:
    sentinel = _make_sentinel()
    original = sentinel.storage
    tracer = FakeTracer()
    exporter = OTelExporter(
        sentinel, endpoint="http://fake:4317", tracer_factory=lambda: tracer
    )

    # storage is now the wrapper
    wrapper = sentinel.storage
    assert wrapper is not original
    assert wrapper.backend_name == original.backend_name

    # initialise is delegated (idempotent for SQLite :memory:)
    wrapper.initialise()

    # Write a trace and look it up via the wrapper
    @sentinel.trace
    def do_work() -> dict[str, int]:
        return {"ok": 1}

    do_work()
    _wait_for_spans(tracer, 1)

    traces = sentinel.query(limit=1)
    assert len(traces) == 1
    loaded = wrapper.get(traces[0].trace_id)
    assert loaded is not None
    assert loaded.trace_id == traces[0].trace_id

    exporter.shutdown()


# ---------------------------------------------------------------------------
# Policy result attribute — when policy_evaluation is present
# ---------------------------------------------------------------------------


def test_otel_span_policy_result_from_evaluation() -> None:
    """When a rule evaluator runs, the span reflects the real ALLOW value."""
    from sentinel.policy.evaluator import SimpleRuleEvaluator

    def rule(inputs: dict) -> tuple[bool, str | None]:
        return True, None

    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        policy_evaluator=SimpleRuleEvaluator({"p.py": rule}),
        project="otel-policy",
        sovereign_scope="EU",
        data_residency=DataResidency.LOCAL,
    )
    tracer = FakeTracer()
    exporter = OTelExporter(
        sentinel, endpoint="http://fake:4317", tracer_factory=lambda: tracer
    )

    @sentinel.trace(policy="p.py")
    def do_work() -> dict[str, int]:
        return {"ok": 1}

    do_work()
    _wait_for_spans(tracer, 1)

    attrs = tracer.spans[0].attributes
    assert attrs["sentinel.policy_result"] == "ALLOW"
    exporter.shutdown()


# ---------------------------------------------------------------------------
# flush + shutdown lifecycle
# ---------------------------------------------------------------------------


def test_otel_flush_drains_queue() -> None:
    sentinel = _make_sentinel()
    tracer = FakeTracer()
    exporter = OTelExporter(
        sentinel, endpoint="http://fake:4317", tracer_factory=lambda: tracer
    )

    @sentinel.trace
    def do_work() -> dict[str, int]:
        return {"ok": 1}

    for _ in range(3):
        do_work()

    exporter.flush(timeout=1.0)
    # After flush the worker should have emitted all enqueued spans
    assert len(tracer.spans) == 3
    exporter.shutdown()


def test_otel_flush_returns_promptly_when_already_empty() -> None:
    sentinel = _make_sentinel()
    tracer = FakeTracer()
    exporter = OTelExporter(
        sentinel, endpoint="http://fake:4317", tracer_factory=lambda: tracer
    )
    # Flushing an empty queue must not hang
    exporter.flush(timeout=0.5)
    exporter.shutdown()


# ---------------------------------------------------------------------------
# _import_otel — the real import path
# ---------------------------------------------------------------------------


def test_import_otel_raises_with_pip_extra_hint_when_sdk_missing() -> None:
    """In this test environment opentelemetry-sdk is not installed, so
    the real _import_otel() must raise ImportError naming the extra."""
    import sentinel.integrations.otel as otel_mod

    try:
        import opentelemetry  # noqa: F401

        pytest.skip("opentelemetry is installed — this test only runs without it")
    except ImportError:
        pass

    with pytest.raises(ImportError, match="sentinel-kernel\\[otel\\]"):
        otel_mod._import_otel()


# ---------------------------------------------------------------------------
# _build_real_tracer — cover the SDK-import branch with fake modules
# ---------------------------------------------------------------------------


def test_build_real_tracer_uses_import_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stub _import_otel() with fake OTel classes so we can cover the
    _build_real_tracer body without installing opentelemetry-sdk."""
    import sentinel.integrations.otel as otel_mod

    sentinel_tracer_obj: list[Any] = []

    class FakeProvider:
        def __init__(self) -> None:
            self.processors: list[Any] = []

        def add_span_processor(self, processor: Any) -> None:
            self.processors.append(processor)

    class FakeProcessor:
        def __init__(self, exporter: Any) -> None:
            self.exporter = exporter

    class FakeExporter:
        def __init__(self, endpoint: str) -> None:
            self.endpoint = endpoint

    class FakeOTelTrace:
        _provider: Any = None

        def set_tracer_provider(self, provider: Any) -> None:
            self._provider = provider

        def get_tracer(self, name: str) -> FakeTracer:
            tracer = FakeTracer()
            sentinel_tracer_obj.append(tracer)
            return tracer

    fake_trace = FakeOTelTrace()

    def fake_import() -> tuple[Any, Any, Any]:
        return fake_trace, (FakeProvider, FakeProcessor), FakeExporter

    monkeypatch.setattr(otel_mod, "_import_otel", fake_import)

    sentinel = _make_sentinel()
    exporter = OTelExporter(sentinel, endpoint="http://stub:4317")

    # _build_real_tracer was invoked because we passed no tracer_factory
    assert sentinel_tracer_obj, "get_tracer was not called"
    assert fake_trace._provider is not None
    # Processor was added
    assert fake_trace._provider.processors
    exporter.shutdown()
