"""
sentinel.integrations.haystack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Haystack integration for Sentinel.

Sovereignty posture:
  - Company: deepset GmbH
  - Jurisdiction: EU (Berlin, Germany)
  - CLOUD Act exposure: None
  - Air-gap capable: Yes (when used with local components)
  - Runtime network calls: Only if using cloud-backed components
  - Critical path: Optional integration — not mandatory
  - License: Apache 2.0

Install: pip install sentinel-kernel[haystack]

Usage::

    from sentinel import Sentinel
    from sentinel.integrations.haystack import SentinelHaystackCallback

    sentinel = Sentinel()
    callback = SentinelHaystackCallback(sentinel=sentinel)

    # Hook into a Haystack Pipeline — pass via its native callback API,
    # or manually record component completions via callback.on_component_end():
    #
    #     callback.on_component_start("reader", {"query": "..."})
    #     # ... run your component ...
    #     callback.on_component_end("reader", {"answer": "..."})
    #
    # A trace is recorded for every component end event.

Haystack is deepset GmbH's (Berlin) agent/RAG framework. It is the
EU-sovereign alternative to LangChain/LlamaIndex/CrewAI/AutoGen.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from sentinel.core.trace import DecisionTrace

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


_MISSING_DEP_MESSAGE = (
    "SentinelHaystackCallback requires haystack-ai. Install the extra:\n"
    "    pip install sentinel-kernel[haystack]"
)


def _require_haystack() -> None:
    """Import haystack-ai; raise a helpful ImportError if missing."""
    try:
        import haystack  # noqa: F401
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc


class SentinelHaystackCallback:
    """
    Callback adapter that writes a DecisionTrace for every Haystack
    component completion routed through it.

    This class is framework-version-agnostic: it exposes
    ``on_component_start(name, inputs)`` and
    ``on_component_end(name, outputs)`` methods that can be invoked
    from a Haystack Pipeline's own callback mechanism, from a
    decorator wrapper, or manually from user code. Sentinel records
    a trace on every ``on_component_end`` call with the component
    name as the agent and the inputs/outputs as the trace payload.

    The component-level granularity is intentional: Haystack's RAG
    and agent pipelines are graphs of components, so a trace per
    component end gives you the full decision history of a
    pipeline run.
    """

    def __init__(self, sentinel: Sentinel) -> None:
        _require_haystack()
        self.sentinel = sentinel
        self._starts: dict[str, float] = {}
        self._inputs: dict[str, dict[str, Any]] = {}

    def on_component_start(
        self,
        component_name: str,
        inputs: dict[str, Any] | None = None,
    ) -> None:
        """Record the start time and inputs for a component run."""
        self._starts[component_name] = time.monotonic()
        self._inputs[component_name] = dict(inputs or {})

    def on_component_end(
        self,
        component_name: str,
        outputs: dict[str, Any] | None = None,
    ) -> None:
        """Write a DecisionTrace on component completion."""
        start = self._starts.pop(component_name, None)
        inputs = self._inputs.pop(component_name, {})
        latency_ms = int((time.monotonic() - start) * 1000) if start else 0

        trace = DecisionTrace(
            project=self.sentinel.project,
            agent=f"haystack.{component_name}",
            inputs=inputs,
            data_residency=self.sentinel.data_residency,
            sovereign_scope=self.sentinel.sovereign_scope,
            storage_backend=self.sentinel.storage.backend_name,
            model_name=inputs.get("model") if isinstance(inputs.get("model"), str) else None,
            model_provider="haystack",
            tags={"integration": "haystack", "vendor": "deepset"},
        )
        trace.complete(
            output=dict(outputs or {}),
            latency_ms=latency_ms,
        )
        self.sentinel.storage.save(trace)

    # ----- Pipeline convenience --------------------------------------

    def wrap_pipeline_run(
        self,
        pipeline: Any,
        *,
        inputs: dict[str, Any],
    ) -> Any:
        """
        Convenience wrapper: run a Haystack ``Pipeline`` and emit a
        single trace covering the full pipeline execution.

        Component-level tracing should use ``on_component_start`` /
        ``on_component_end`` in a callback registered with the
        pipeline. This method is the coarse-grained equivalent for
        users who only want one trace per pipeline run.
        """
        start = time.monotonic()
        self.on_component_start("pipeline", inputs)
        try:
            result = pipeline.run(inputs)
        except Exception as exc:
            self.on_component_end("pipeline", {"error": repr(exc)})
            raise
        latency_ms = int((time.monotonic() - start) * 1000)
        outputs = result if isinstance(result, dict) else {"result": repr(result)}
        outputs["_latency_ms"] = latency_ms
        self.on_component_end("pipeline", outputs)
        return result
