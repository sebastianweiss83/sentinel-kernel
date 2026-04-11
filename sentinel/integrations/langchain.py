"""
sentinel.integrations.langchain
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
LangChain callback handler that records a DecisionTrace for every
LLM / chain call routed through LangChain.

Optional dependency: langchain-core. Install with:

    pip install sentinel-kernel[langchain]

Sovereignty note: LangChain is a US-owned framework. This integration
is an **optional** convenience wrapper for teams already committed to
LangChain. It is not in the Sentinel critical path and not part of
the default import surface.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sentinel.core.trace import DecisionTrace

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel


_MISSING_DEP_MESSAGE = (
    "SentinelCallbackHandler requires langchain-core. Install the extra:\n"
    "    pip install sentinel-kernel[langchain]"
)


def _import_base_callback_handler() -> Any:
    try:
        from langchain_core.callbacks import BaseCallbackHandler
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc
    return BaseCallbackHandler


# Resolve the base class at import time so SentinelCallbackHandler can inherit
# from it when langchain-core is available. When langchain-core is missing,
# fall back to a marker base so the class is still importable and the real
# ImportError is raised at instantiation time with a helpful message.
try:  # pragma: no cover - environment dependent
    from langchain_core.callbacks import BaseCallbackHandler as _BaseCallbackHandler
    _HAS_LANGCHAIN = True
except ImportError:  # pragma: no cover - hit only when extra not installed
    _HAS_LANGCHAIN = False

    class _BaseCallbackHandler:  # type: ignore[no-redef]
        """Stub base class used when langchain-core is not installed."""


class SentinelCallbackHandler(_BaseCallbackHandler):
    """
    LangChain callback handler that writes a DecisionTrace on every
    ``on_llm_end`` and ``on_chain_end`` event using the given Sentinel
    instance's storage and sovereignty metadata.

    Usage::

        from sentinel import Sentinel
        from sentinel.integrations.langchain import SentinelCallbackHandler

        sentinel = Sentinel()
        handler = SentinelCallbackHandler(sentinel=sentinel)

        # LangChain components accept callbacks
        llm = ChatOpenAI(callbacks=[handler])
    """

    def __init__(self, sentinel: Sentinel) -> None:
        if not _HAS_LANGCHAIN:
            raise ImportError(_MISSING_DEP_MESSAGE)
        self.sentinel = sentinel
        self._starts: dict[str, float] = {}
        self._prompts: dict[str, list[str]] = {}
        self._models: dict[str, str] = {}

    # ----- LLM hooks --------------------------------------------------------

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        key = str(run_id) if run_id is not None else "_singleton"
        self._starts[key] = time.monotonic()
        self._prompts[key] = list(prompts)
        self._models[key] = _extract_model_name(serialized, kwargs)

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        key = str(run_id) if run_id is not None else "_singleton"
        start = self._starts.pop(key, None)
        prompts = self._prompts.pop(key, [])
        model = self._models.pop(key, "unknown")
        latency_ms = int((time.monotonic() - start) * 1000) if start else 0

        output = _serialise_llm_result(response)
        self._record(
            agent="langchain.llm",
            model=model,
            inputs={"prompts": prompts},
            output=output,
            latency_ms=latency_ms,
        )

    # ----- Chain hooks ------------------------------------------------------

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        key = str(run_id) if run_id is not None else "_singleton_chain"
        self._starts[key] = time.monotonic()
        self._prompts[key] = [repr(inputs)]
        self._models[key] = _extract_model_name(serialized, kwargs)

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        key = str(run_id) if run_id is not None else "_singleton_chain"
        start = self._starts.pop(key, None)
        inputs_repr = self._prompts.pop(key, [])
        model = self._models.pop(key, "chain")
        latency_ms = int((time.monotonic() - start) * 1000) if start else 0

        self._record(
            agent="langchain.chain",
            model=model,
            inputs={"inputs": inputs_repr},
            output=dict(outputs) if isinstance(outputs, dict) else {"result": repr(outputs)},
            latency_ms=latency_ms,
        )

    # ----- Internal ---------------------------------------------------------

    def _record(
        self,
        *,
        agent: str,
        model: str,
        inputs: dict[str, Any],
        output: dict[str, Any],
        latency_ms: int,
    ) -> None:
        trace = DecisionTrace(
            project=self.sentinel.project,
            agent=agent,
            inputs=inputs,
            data_residency=self.sentinel.data_residency,
            sovereign_scope=self.sentinel.sovereign_scope,
            storage_backend=self.sentinel.storage.backend_name,
            model_name=model,
            model_provider="langchain",
            tags={"integration": "langchain"},
        )
        trace.complete(output=output, latency_ms=latency_ms)
        self.sentinel.storage.save(trace)


def _extract_model_name(serialized: dict[str, Any] | None, kwargs: dict[str, Any]) -> str:
    if serialized:
        for key in ("name", "id"):
            value = serialized.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list) and value:
                return str(value[-1])
        kwargs_section = serialized.get("kwargs") or {}
        model = kwargs_section.get("model") or kwargs_section.get("model_name")
        if isinstance(model, str):
            return model
    invocation = kwargs.get("invocation_params") or {}
    if isinstance(invocation, dict):
        model = invocation.get("model") or invocation.get("model_name")
        if isinstance(model, str):
            return model
    return "unknown"


def _serialise_llm_result(response: Any) -> dict[str, Any]:
    """Turn a LangChain LLMResult (or equivalent) into a plain dict."""
    generations = getattr(response, "generations", None)
    if generations is None:
        return {"result": repr(response)}
    flat: list[str] = []
    for group in generations:
        for gen in group:
            text = getattr(gen, "text", None)
            if text is None:
                text = repr(gen)
            flat.append(text)
    return {"generations": flat}
