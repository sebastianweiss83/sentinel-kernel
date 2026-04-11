"""CrewAI integration for Sentinel.

Sovereignty posture:
    CrewAI: MIT license
    Company: CrewAI Inc (US) — library only, no runtime cloud calls
    CLOUD Act: only if using external cloud LLMs or CrewAI cloud
    Air-gap: YES with a local LLM (Ollama, llama.cpp, etc.)

Install::

    pip install sentinel-kernel[crewai]

Usage::

    from sentinel.integrations.crewai import SentinelCrewCallback

    callback = SentinelCrewCallback(sentinel=my_sentinel)
    # Attach to a CrewAI Task:
    #   task = Task(description=..., callbacks=[callback.task_callback])
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from sentinel.core.trace import DecisionTrace

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel

_MISSING_DEP_MESSAGE = (
    "SentinelCrewCallback requires crewai. Install the extra:\n"
    "    pip install sentinel-kernel[crewai]"
)

try:  # pragma: no cover - environment dependent
    import crewai as _crewai  # noqa: F401

    _HAS_CREWAI = True
except ImportError:  # pragma: no cover - hit only when extra not installed
    _HAS_CREWAI = False


class SentinelCrewCallback:
    """Records a :class:`DecisionTrace` on every CrewAI task completion."""

    def __init__(
        self,
        sentinel: Sentinel,
        sovereign_scope: str = "EU",
        data_residency: str = "local",
    ) -> None:
        if not _HAS_CREWAI:
            raise ImportError(_MISSING_DEP_MESSAGE)
        self.sentinel = sentinel
        self.sovereign_scope = sovereign_scope
        self.data_residency = data_residency
        self._start = time.monotonic()

    def task_callback(self, output: Any) -> None:
        """Callable suitable as a CrewAI ``Task`` callback."""
        latency_ms = int((time.monotonic() - self._start) * 1000)
        self._start = time.monotonic()
        trace = DecisionTrace(
            project=self.sentinel.project,
            agent="crewai_task",
            inputs={"output_type": type(output).__name__},
            data_residency=self.sentinel.data_residency,
            sovereign_scope=self.sentinel.sovereign_scope,
            storage_backend=self.sentinel.storage.backend_name,
            tags={
                "integration": "crewai",
                "sovereign_scope": self.sovereign_scope,
                "data_residency": self.data_residency,
            },
        )
        trace.complete(output=_serialise_output(output), latency_ms=latency_ms)
        self.sentinel.storage.save(trace)


def _serialise_output(output: Any) -> dict[str, Any]:
    if isinstance(output, dict):
        return dict(output)
    return {"result": repr(output), "type": type(output).__name__}
