"""
sentinel.integrations.otel
~~~~~~~~~~~~~~~~~~~~~~~~~~
OpenTelemetry exporter: emits an OTel span for every DecisionTrace
written through a wrapped Sentinel storage backend.

Span name:      sentinel.decision
Span attributes: sentinel.trace_id, sentinel.agent, sentinel.policy_result,
                 sentinel.sovereign_scope, sentinel.data_residency,
                 sentinel.latency_ms, sentinel.schema_version

Export runs on a background worker thread. Failures are logged and
swallowed — a broken OTel collector must not crash the decision path.

Optional dependency: opentelemetry-sdk + opentelemetry-exporter-otlp.
Install with: pip install sentinel-kernel[otel]

Sovereignty note: OpenTelemetry is a CNCF project. The OTLP protocol
is open and vendor-neutral. You can point this exporter at a self-hosted
collector running on EU-sovereign infrastructure.
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import TYPE_CHECKING, Any

from sentinel.storage.base import StorageBackend

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace, PolicyResult
    from sentinel.core.tracer import Sentinel


log = logging.getLogger("sentinel.otel")

_MISSING_DEP_MESSAGE = (
    "OTelExporter requires opentelemetry-sdk and opentelemetry-exporter-otlp.\n"
    "Install the extra:\n"
    "    pip install sentinel-kernel[otel]"
)


def _import_otel() -> tuple[Any, Any, Any]:  # pragma: no cover
    try:
        from opentelemetry import trace as otel_trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc
    return otel_trace, (TracerProvider, BatchSpanProcessor), OTLPSpanExporter


class _OTelStorageWrapper(StorageBackend):
    """
    Decorator around a StorageBackend that also emits an OTel span on every save.

    We wrap the storage rather than monkey-patching the Sentinel instance so
    export is transparent to the rest of the kernel.
    """

    def __init__(self, inner: StorageBackend, exporter: OTelExporter) -> None:
        self._inner = inner
        self._exporter = exporter

    @property
    def backend_name(self) -> str:
        return self._inner.backend_name

    def initialise(self) -> None:
        self._inner.initialise()

    def save(self, trace: DecisionTrace) -> None:
        self._inner.save(trace)
        self._exporter._enqueue(trace)

    def query(
        self,
        project: str | None = None,
        agent: str | None = None,
        policy_result: PolicyResult | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DecisionTrace]:
        return self._inner.query(
            project=project,
            agent=agent,
            policy_result=policy_result,
            limit=limit,
            offset=offset,
        )

    def get(self, trace_id: str) -> DecisionTrace | None:
        return self._inner.get(trace_id)


class OTelExporter:
    """
    Background OpenTelemetry exporter for Sentinel decision traces.

    Wrapping a Sentinel instance causes every subsequent ``storage.save()``
    to emit a span named ``sentinel.decision`` with sovereignty attributes.

    Usage::

        from sentinel import Sentinel
        from sentinel.integrations.otel import OTelExporter

        sentinel = Sentinel()
        exporter = OTelExporter(sentinel, endpoint="http://localhost:4317")
        # traces now flow to both the local storage AND the OTel collector
    """

    def __init__(
        self,
        sentinel: Sentinel,
        endpoint: str,
        *,
        tracer_factory: Any = None,
        service_name: str = "sentinel",
    ) -> None:
        """
        :param sentinel: the Sentinel instance to hook.
        :param endpoint: OTLP/gRPC endpoint, e.g. ``http://localhost:4317``.
        :param tracer_factory: optional callable returning an OTel tracer
            (used in tests to inject a fake).
        :param service_name: OTel service.name resource attribute.
        """
        self.endpoint = endpoint
        self.service_name = service_name
        self._queue: queue.Queue[DecisionTrace | None] = queue.Queue()
        self._stop = threading.Event()

        if tracer_factory is None:
            self._tracer = self._build_real_tracer()
        else:
            self._tracer = tracer_factory()

        self._worker = threading.Thread(
            target=self._run, name="sentinel-otel-exporter", daemon=True
        )
        self._worker.start()

        # Wrap the Sentinel storage so every save also emits a span.
        sentinel.storage = _OTelStorageWrapper(sentinel.storage, self)

    # ----- Tracer setup -----------------------------------------------------

    def _build_real_tracer(self) -> Any:
        otel_trace, (TracerProvider, BatchSpanProcessor), OTLPSpanExporter = _import_otel()
        provider = TracerProvider()
        try:
            exporter = OTLPSpanExporter(endpoint=self.endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("OTel exporter setup failed, spans will be dropped: %s", exc)
        otel_trace.set_tracer_provider(provider)
        return otel_trace.get_tracer(self.service_name)

    # ----- Enqueue / worker -------------------------------------------------

    def _enqueue(self, trace: DecisionTrace) -> None:
        self._queue.put(trace)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                trace = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if trace is None:
                break
            self._emit_span(trace)

    def _emit_span(self, trace: DecisionTrace) -> None:
        try:
            with self._tracer.start_as_current_span("sentinel.decision") as span:
                _set_span_attributes(span, trace)
        except Exception as exc:
            log.warning("OTel span export failed (swallowed): %s", exc)

    # ----- Lifecycle --------------------------------------------------------

    def flush(self, timeout: float = 1.0) -> None:
        """Block until the queue is drained (used in tests)."""
        self._queue.join() if False else None  # no-op placeholder
        deadline = threading.Event()
        t = threading.Timer(timeout, deadline.set)
        t.daemon = True
        t.start()
        try:
            while not deadline.is_set() and not self._queue.empty():
                deadline.wait(0.01)
        finally:
            t.cancel()

    def shutdown(self) -> None:
        self._stop.set()
        self._queue.put(None)
        self._worker.join(timeout=1.0)


def _set_span_attributes(span: Any, trace: DecisionTrace) -> None:
    policy_result = "NOT_EVALUATED"
    if trace.policy_evaluation:
        policy_result = trace.policy_evaluation.result.value

    span.set_attribute("sentinel.trace_id", trace.trace_id)
    span.set_attribute("sentinel.agent", trace.agent)
    span.set_attribute("sentinel.policy_result", policy_result)
    span.set_attribute("sentinel.sovereign_scope", trace.sovereign_scope)
    span.set_attribute("sentinel.data_residency", trace.data_residency.value)
    span.set_attribute("sentinel.latency_ms", int(trace.latency_ms or 0))
    span.set_attribute("sentinel.schema_version", trace.schema_version)
