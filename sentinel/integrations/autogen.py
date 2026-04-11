"""Microsoft AutoGen integration for Sentinel.

Sovereignty posture:
    AutoGen: MIT license (Microsoft, US)
    CLOUD Act: ONLY if using Azure OpenAI or LangSmith tracing
    The AutoGen library itself makes no network calls
    Air-gap: YES with a local LLM

Sentinel wraps ``generate_reply`` — every agent message becomes a
sovereign DecisionTrace. No changes to existing AutoGen code.

Install::

    pip install sentinel-kernel[autogen]

Usage::

    from sentinel.integrations.autogen import SentinelAutoGenHook

    hook = SentinelAutoGenHook(sentinel=my_sentinel)
    hook.register(agent)  # wraps ``generate_reply`` silently
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sentinel.core.trace import DecisionTrace

if TYPE_CHECKING:
    from sentinel.core.tracer import Sentinel

_MISSING_DEP_MESSAGE = (
    "SentinelAutoGenHook requires pyautogen. Install the extra:\n"
    "    pip install sentinel-kernel[autogen]"
)

try:  # pragma: no cover - environment dependent
    import autogen as _autogen  # noqa: F401

    _HAS_AUTOGEN = True
except ImportError:  # pragma: no cover - hit only when extra not installed
    _HAS_AUTOGEN = False


class SentinelAutoGenHook:
    """Wraps an AutoGen agent's ``generate_reply`` to record traces."""

    def __init__(
        self,
        sentinel: Sentinel,
        sovereign_scope: str = "EU",
    ) -> None:
        if not _HAS_AUTOGEN:
            raise ImportError(_MISSING_DEP_MESSAGE)
        self.sentinel = sentinel
        self.sovereign_scope = sovereign_scope

    def register(self, agent: Any) -> None:
        """Wrap ``agent.generate_reply`` with sovereign trace capture."""
        original = getattr(agent, "generate_reply", None)
        if original is None:
            raise AttributeError("agent has no generate_reply method")

        sentinel = self.sentinel
        scope = self.sovereign_scope

        def governed_reply(messages: Any = None, **kwargs: Any) -> Any:
            start = time.monotonic()
            started_at = datetime.now(UTC)
            response = original(messages=messages, **kwargs)
            latency_ms = int((time.monotonic() - start) * 1000)

            trace = DecisionTrace(
                project=sentinel.project,
                agent=f"autogen:{getattr(agent, 'name', 'agent')}",
                started_at=started_at,
                inputs={"message_count": len(messages) if messages else 0},
                data_residency=sentinel.data_residency,
                sovereign_scope=sentinel.sovereign_scope,
                storage_backend=sentinel.storage.backend_name,
                tags={"integration": "autogen", "sovereign_scope": scope},
            )
            trace.complete(
                output={"response": repr(response)[:500]},
                latency_ms=latency_ms,
            )
            sentinel.storage.save(trace)
            return response

        agent.generate_reply = governed_reply
