"""
sentinel.integrations.langfuse
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
LangFuse enrichment: attach Sentinel sovereignty metadata to an existing
LangFuse trace using the shared trace id as the join key.

Division of concerns:
    LangFuse   — what did the model say, how did it perform
    Sentinel   — what was decided, under which policy, under whose law

Optional dependency: langfuse. Install with:
    pip install sentinel-kernel[langfuse]

Sovereignty note: LangFuse is Berlin-based and self-hostable. A self-hosted
LangFuse deployment on EU infrastructure passes all three sovereignty tests.
LangFuse Cloud is shared infrastructure — evaluate carefully.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace
    from sentinel.core.tracer import Sentinel


_MISSING_DEP_MESSAGE = (
    "LangFuseEnricher requires langfuse. Install the extra:\n"
    "    pip install sentinel-kernel[langfuse]"
)


def _import_langfuse_client() -> Any:
    try:
        from langfuse import Langfuse
    except ImportError as exc:
        raise ImportError(_MISSING_DEP_MESSAGE) from exc
    return Langfuse


class LangFuseEnricher:
    """
    Enrich a LangFuse trace with Sentinel sovereignty metadata.

    Usage::

        enricher = LangFuseEnricher(sentinel)
        # after your agent runs and produces both a LangFuse trace and
        # a Sentinel decision trace:
        enricher.enrich(
            langfuse_trace_id="lf_abc123",
            sentinel_trace_id="01hx7k9m2n3p4q5r6s7t8u9v0w",
        )

    The LangFuse trace gains the following metadata keys:
        sentinel.trace_id
        sentinel.sovereign_scope
        sentinel.data_residency
        sentinel.policy
        sentinel.policy_result
        sentinel.policy_rule
        sentinel.agent
        sentinel.schema_version
    """

    def __init__(self, sentinel: Sentinel, *, client: Any = None) -> None:
        self.sentinel = sentinel
        if client is None:
            Langfuse = _import_langfuse_client()
            self._client = Langfuse()
        else:
            self._client = client

    def enrich(self, langfuse_trace_id: str, sentinel_trace_id: str) -> dict[str, Any]:
        """
        Attach sovereignty metadata to a LangFuse trace.

        :returns: the metadata dict that was applied (also returned so callers
            and tests can assert on the exact shape without re-querying).
        :raises KeyError: if the Sentinel trace id is not in storage.
        """
        trace = self.sentinel.storage.get(sentinel_trace_id)
        if trace is None:
            raise KeyError(
                f"Sentinel trace not found: {sentinel_trace_id}. "
                f"Has it been written yet?"
            )

        metadata = _build_metadata(trace)
        self._apply_metadata(langfuse_trace_id, metadata)
        return metadata

    def join_key(self, sentinel_trace_id: str) -> str:
        """
        The canonical join key between LangFuse and Sentinel.

        Sentinel trace_id == LangFuse external_id. Writing the Sentinel
        trace_id as the LangFuse external_id at LLM-call time makes
        enrichment a direct lookup later.
        """
        return sentinel_trace_id

    def _apply_metadata(self, langfuse_trace_id: str, metadata: dict[str, Any]) -> None:
        """Call whatever LangFuse client method applies metadata to a trace."""
        # The LangFuse SDK has shuffled naming between major versions. We
        # probe a few call shapes so the enricher survives minor upgrades.
        client = self._client
        if hasattr(client, "trace"):
            # Legacy SDK: client.trace(id=..., metadata=...)
            client.trace(id=langfuse_trace_id, metadata=metadata)
            return
        if hasattr(client, "update_trace"):
            client.update_trace(trace_id=langfuse_trace_id, metadata=metadata)
            return
        if hasattr(client, "update"):
            client.update(trace_id=langfuse_trace_id, metadata=metadata)
            return
        raise AttributeError(
            "LangFuse client does not expose a known metadata update method. "
            "Supported methods: trace(), update_trace(), update()."
        )


def _build_metadata(trace: DecisionTrace) -> dict[str, Any]:
    policy_id = None
    policy_result = None
    policy_rule = None
    if trace.policy_evaluation:
        policy_id = trace.policy_evaluation.policy_id
        policy_result = trace.policy_evaluation.result.value
        policy_rule = trace.policy_evaluation.rule_triggered

    return {
        "sentinel.trace_id": trace.trace_id,
        "sentinel.sovereign_scope": trace.sovereign_scope,
        "sentinel.data_residency": trace.data_residency.value,
        "sentinel.policy": policy_id,
        "sentinel.policy_result": policy_result,
        "sentinel.policy_rule": policy_rule,
        "sentinel.agent": trace.agent,
        "sentinel.schema_version": trace.schema_version,
    }
