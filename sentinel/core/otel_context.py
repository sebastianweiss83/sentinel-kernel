"""Capture W3C Trace Context from the active OpenTelemetry span, if any.

The bridge direction is **ingress only**: Sentinel reads context that a
caller already established via OpenTelemetry and records the identifiers
on the outgoing :class:`DecisionTrace`. Sentinel does not create OTEL
spans in this direction — that would overstep into being an observability
tool. The `sentinel.integrations.otel.OTelExporter` handles the reverse
direction (Sentinel → OTEL spans) and is unchanged.

See :doc:`docs/architecture/v3.5-item-1-causal-context` for the full
design rationale.
"""

from __future__ import annotations

from dataclasses import dataclass

try:  # pragma: no cover - environment dependent
    from opentelemetry import trace as _otel_trace

    _HAS_OTEL = True
except ImportError:  # pragma: no cover - only when opentelemetry-api missing
    _HAS_OTEL = False
    _otel_trace = None  # type: ignore[assignment]


@dataclass(frozen=True)
class OtelContext:
    """The three W3C Trace Context identifiers captured per trace.

    Hex-encoded per W3C traceparent spec: 32 chars for ``trace_id``,
    16 chars for ``span_id`` and (when present) ``parent_span_id``.
    Immutable so the captured snapshot can't drift mid-execution.
    """

    trace_id: str
    span_id: str
    parent_span_id: str | None


def _format_trace_id(value: int) -> str:
    return f"{value:032x}"


def _format_span_id(value: int) -> str:
    return f"{value:016x}"


def capture_current_otel_context() -> OtelContext | None:
    """Snapshot the active OTEL span's context, or return None.

    Returns None when:

    - ``opentelemetry-api`` isn't installed (Sentinel stays
      dependency-free in the default install)
    - There is no active span
    - The active span is ``INVALID_SPAN`` (OTEL's no-op sentinel) or
      otherwise has a zero-valued trace_id

    Never raises. A trace that can't capture OTEL context is still a
    valid trace; the absence of a cross-system identifier is not a
    failure condition.
    """
    if not _HAS_OTEL:
        return None

    span = _otel_trace.get_current_span()
    if span is None:  # pragma: no cover - OTEL returns INVALID_SPAN, never None
        return None

    try:
        ctx = span.get_span_context()
    except Exception:  # pragma: no cover - defensive; OTEL may evolve
        return None

    # INVALID_SPAN and zeroed contexts share the same shape — a zero
    # trace_id — so one check handles both.
    if not ctx or ctx.trace_id == 0:
        return None

    parent_span_id: str | None = None
    # ``span.parent`` is the enclosing-span SpanContext when this is a
    # child span, or None/invalid for root spans. Shape varies across
    # OTEL SDK vs. API-only installs, so we look it up defensively.
    parent_ctx = getattr(span, "parent", None)
    if parent_ctx is not None:
        parent_span_id_raw = getattr(parent_ctx, "span_id", 0)
        if parent_span_id_raw:
            parent_span_id = _format_span_id(parent_span_id_raw)

    return OtelContext(
        trace_id=_format_trace_id(ctx.trace_id),
        span_id=_format_span_id(ctx.span_id),
        parent_span_id=parent_span_id,
    )


__all__ = ["OtelContext", "capture_current_otel_context"]
