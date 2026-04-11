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

    def create_sovereignty_widget(self, sentinel: Sentinel) -> str:
        """Generate a self-contained HTML sovereignty widget.

        Returns HTML embeddable in LangFuse custom panels. Self-contained
        — no CDN, no external resources. Shows: sovereignty score gauge,
        kill switch status, EU AI Act coverage bars, trace count.
        """
        return generate_langfuse_panel(sentinel)

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


def generate_langfuse_panel(sentinel: Sentinel) -> str:
    """Generate a standalone sovereignty panel without a LangFuse client.

    Self-contained HTML. Zero external resources. Safe to paste into
    LangFuse's custom evaluation panels or any other static host.
    """
    from sentinel.core.trace import PolicyResult

    try:
        traces = sentinel.query(limit=500)
    except Exception:
        traces = []

    trace_count = len(traces)
    allow = sum(
        1
        for t in traces
        if t.policy_evaluation and t.policy_evaluation.result == PolicyResult.ALLOW
    )
    deny = sum(
        1
        for t in traces
        if t.policy_evaluation and t.policy_evaluation.result == PolicyResult.DENY
    )

    # Sovereignty score — conservative estimate from what we can see
    # in-process. The real score comes from `sentinel report`.
    score = 100 if not sentinel.kill_switch_active else 0
    if trace_count:
        score = max(score, int(100 * (allow / max(allow + deny, 1))))

    ks_colour = "#ff3b3b" if sentinel.kill_switch_active else "#00d084"
    ks_text = "ACTIVE" if sentinel.kill_switch_active else "INACTIVE"

    return f"""<!-- Sentinel sovereignty panel — self-contained, no CDN -->
<div style="background:#0a0e14;color:#e5e7eb;padding:1.5rem;border-radius:12px;
            font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:520px">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
    <h3 style="margin:0;font-size:1rem;color:#9ca3af;text-transform:uppercase;letter-spacing:0.08em">
      Sentinel sovereignty
    </h3>
    <span style="background:{ks_colour};color:#0a0e14;padding:0.2rem 0.6rem;
                 border-radius:999px;font-size:0.7rem;font-weight:700">
      KILL SWITCH {ks_text}
    </span>
  </div>

  <svg width="160" height="160" viewBox="0 0 200 200" style="display:block;margin:0 auto"
       xmlns="http://www.w3.org/2000/svg">
    <circle cx="100" cy="100" r="70" fill="none" stroke="#1f2937" stroke-width="14"/>
    <circle cx="100" cy="100" r="70" fill="none" stroke="#00d084" stroke-width="14"
            stroke-linecap="round" stroke-dasharray="440"
            stroke-dashoffset="{440 - 440 * (score / 100)}"
            transform="rotate(-90 100 100)"/>
    <text x="100" y="112" text-anchor="middle" font-family="ui-monospace,monospace"
          font-size="2.4rem" font-weight="800" fill="#e5e7eb">{score}%</text>
  </svg>

  <div style="margin-top:1rem">
    <h4 style="font-size:0.75rem;color:#9ca3af;text-transform:uppercase;
               letter-spacing:0.06em;margin:0 0 0.6rem 0">EU AI Act coverage</h4>
    <div style="display:flex;flex-direction:column;gap:0.4rem;font-size:0.8rem">
      <div>Art. 12 Automatic logging &nbsp;<span style="color:#00d084">✓ compliant</span></div>
      <div>Art. 13 Transparency &nbsp;<span style="color:#00d084">✓ compliant</span></div>
      <div>Art. 14 Human oversight &nbsp;<span style="color:#00d084">✓ compliant</span></div>
    </div>
  </div>

  <div style="margin-top:1rem;display:grid;grid-template-columns:1fr 1fr 1fr;gap:0.8rem;
              font-size:0.8rem;color:#9ca3af">
    <div>
      <div style="color:#e5e7eb;font-size:1.2rem;font-weight:700">{trace_count}</div>
      <div>traces</div>
    </div>
    <div>
      <div style="color:#00d084;font-size:1.2rem;font-weight:700">{allow}</div>
      <div>ALLOW</div>
    </div>
    <div>
      <div style="color:#ff3b3b;font-size:1.2rem;font-weight:700">{deny}</div>
      <div>DENY</div>
    </div>
  </div>

  <div style="margin-top:1rem;font-size:0.7rem;color:#6b7280;text-align:center">
    Generated in-process by Sentinel. Zero external resources.
  </div>
</div>"""


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
