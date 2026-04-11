"""
09 — OpenTelemetry export.

OTelExporter wraps the Sentinel storage so every decision trace
also produces a `sentinel.decision` OTel span with sovereignty
metadata as span attributes. Optional dependency:

    pip3 install sentinel-kernel[otel]

IMPORTANT: local storage is always written FIRST. OTel is additive
observability; it never replaces the sovereign record. If the OTel
endpoint is unreachable, a warning is logged and the call still
succeeds.

This example uses a fake tracer so no real OTel collector is
required. In production, point the exporter at a collector you
control (e.g. http://localhost:4317).

Run:
    python examples/09_otel_export.py
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from sentinel import DataResidency, Sentinel
from sentinel.integrations.otel import OTelExporter
from sentinel.storage import SQLiteStorage


class FakeSpan:
    def __init__(self, name: str) -> None:
        self.name = name
        self.attrs: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self.attrs[key] = value


class FakeTracer:
    def __init__(self) -> None:
        self.spans: list[FakeSpan] = []

    @contextmanager
    def start_as_current_span(self, name: str) -> Any:
        span = FakeSpan(name)
        self.spans.append(span)
        yield span


def main() -> None:
    sentinel = Sentinel(
        storage=SQLiteStorage(":memory:"),
        project="otel-demo",
        data_residency=DataResidency.EU_DE,
        sovereign_scope="EU",
    )

    tracer = FakeTracer()
    exporter = OTelExporter(
        sentinel, endpoint="http://localhost:4317", tracer_factory=lambda: tracer
    )

    @sentinel.trace
    def work(payload: dict) -> dict:
        return {"processed": payload["id"]}

    for i in range(3):
        work({"id": f"item-{i}"})

    # Background exporter thread — wait briefly for spans to drain
    import time
    for _ in range(100):
        if len(tracer.spans) >= 3:
            break
        time.sleep(0.01)

    exporter.shutdown()

    print(f"Emitted {len(tracer.spans)} OTel spans.")
    print("Span attributes always include the sovereignty fingerprint:")
    if tracer.spans:
        span = tracer.spans[0]
        print(f"  sentinel.sovereign_scope : {span.attrs.get('sentinel.sovereign_scope')}")
        print(f"  sentinel.data_residency  : {span.attrs.get('sentinel.data_residency')}")
        print(f"  sentinel.policy_result   : {span.attrs.get('sentinel.policy_result')}")
        print(f"  sentinel.schema_version  : {span.attrs.get('sentinel.schema_version')}")


if __name__ == "__main__":
    main()
