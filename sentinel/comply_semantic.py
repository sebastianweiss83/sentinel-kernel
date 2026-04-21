"""JSON-LD + PROV-O semantic export for long-term evidence retention.

Builds a JSON-LD document mapping a set of :class:`DecisionTrace`
records onto the W3C PROV-O provenance ontology, extended with a
minimal Sentinel vocabulary for domain-specific concepts (sovereignty
scope, kill switch, signature algorithm, OTEL linkage).

See :doc:`docs/architecture/v3.5-item-2-semantic-export` for the full
design rationale. The published vocabulary lives at
``https://sebastianweiss83.github.io/sentinel-kernel/ontology/v1/`` and
is served as part of the existing GitHub Pages deploy.

The ``[jsonld]`` optional extra pulls :mod:`pyld` for canonical
JSON-LD validation. The generator function will raise a helpful
:class:`ImportError` if the extra isn't installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentinel.core.trace import DecisionTrace

_ONTOLOGY_BASE = "https://sebastianweiss83.github.io/sentinel-kernel/ontology/v1"
_CONTEXT_URL = f"{_ONTOLOGY_BASE}/context.jsonld"
_SNTL_PREFIX = f"{_ONTOLOGY_BASE}/#"
_PROV_PREFIX = "http://www.w3.org/ns/prov#"

_MISSING_DEP_MESSAGE = (
    "JSON-LD export requires `pyld`. Install:\n"
    "    pip install 'sentinel-kernel[jsonld]'\n"
    "\n"
    "pyld is MIT-licensed, pure Python, no native deps — it's used for\n"
    "canonical validation of the emitted document. The @context is\n"
    "inlined so the generated file verifies offline."
)


def _inline_context() -> dict[str, Any]:
    """The Sentinel JSON-LD @context, inlined into every export.

    Shipping the context inline (rather than linking to the public URL)
    keeps evidence packs verifiable offline and immune to future
    ontology redirects. The context matches ``docs/ontology/v1/context.jsonld``
    byte-for-byte.
    """
    return {
        "sntl": _SNTL_PREFIX,
        "prov": _PROV_PREFIX,
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "DecisionTrace": "sntl:DecisionTrace",
        "PolicyEvaluation": "sntl:PolicyEvaluation",
        "HumanOverride": "sntl:HumanOverride",
        "InputsHash": "sntl:InputsHash",
        "OutputHash": "sntl:OutputHash",
        "startedAt": {"@id": "prov:startedAtTime", "@type": "xsd:dateTime"},
        "completedAt": {"@id": "prov:endedAtTime", "@type": "xsd:dateTime"},
        "wasAssociatedWith": {"@id": "prov:wasAssociatedWith", "@type": "@id"},
        "used": {"@id": "prov:used", "@type": "@id"},
        "generated": {"@id": "prov:generated", "@type": "@id"},
        "wasDerivedFrom": {"@id": "prov:wasDerivedFrom", "@type": "@id"},
        "value": {"@id": "prov:value"},
        "agent": "sntl:agent",
        "project": "sntl:project",
        "schemaVersion": "sntl:schemaVersion",
        "signature": "sntl:signature",
        "signatureAlgorithm": "sntl:signatureAlgorithm",
        "sovereignScope": "sntl:sovereignScope",
        "dataResidency": "sntl:dataResidency",
        "storageBackend": "sntl:storageBackend",
        "policyId": "sntl:policyId",
        "policyResult": "sntl:policyResult",
        "ruleTriggered": "sntl:ruleTriggered",
        "policyEvaluation": "sntl:policyEvaluation",
        "otelTraceId": "sntl:otelTraceId",
        "otelSpanId": "sntl:otelSpanId",
        "otelParentSpanId": "sntl:otelParentSpanId",
        "parentTraceId": "sntl:parentTraceId",
        "precedentTraceIds": {"@id": "sntl:precedentTraceIds", "@container": "@set"},
        "tags": "sntl:tags",
        "latencyMs": "sntl:latencyMs",
    }


def _agent_id(trace: DecisionTrace) -> str:
    """Stable IRI for the agent entity across all of this agent's traces."""
    return f"urn:sentinel:agent:{trace.agent}"


def _trace_id(trace: DecisionTrace) -> str:
    return f"urn:sentinel:trace:{trace.trace_id}"


def _inputs_entity_id(trace: DecisionTrace) -> str:
    return f"urn:sentinel:inputs:{trace.trace_id}"


def _output_entity_id(trace: DecisionTrace) -> str:
    return f"urn:sentinel:output:{trace.trace_id}"


def _build_activity_node(trace: DecisionTrace) -> dict[str, Any]:
    """Map one DecisionTrace to its JSON-LD activity node."""
    node: dict[str, Any] = {
        "@id": _trace_id(trace),
        "@type": ["DecisionTrace", "prov:Activity"],
        "schemaVersion": trace.schema_version,
        "project": trace.project,
        "agent": trace.agent,
        "startedAt": trace.started_at.isoformat(),
        "wasAssociatedWith": _agent_id(trace),
        "sovereignScope": trace.sovereign_scope,
        "dataResidency": trace.data_residency.value,
        "storageBackend": trace.storage_backend,
    }

    if trace.completed_at is not None:
        node["completedAt"] = trace.completed_at.isoformat()
    if trace.latency_ms is not None:
        node["latencyMs"] = trace.latency_ms
    if trace.parent_trace_id:
        node["parentTraceId"] = trace.parent_trace_id
    if trace.precedent_trace_ids:
        node["precedentTraceIds"] = list(trace.precedent_trace_ids)
    if trace.signature:
        node["signature"] = trace.signature
    if trace.signature_algorithm:
        node["signatureAlgorithm"] = trace.signature_algorithm
    if trace.tags:
        node["tags"] = dict(trace.tags)

    # v3.5 Item 1 — OTEL causal-context identifiers.
    if trace.otel_trace_id:
        node["otelTraceId"] = trace.otel_trace_id
    if trace.otel_span_id:
        node["otelSpanId"] = trace.otel_span_id
    if trace.otel_parent_span_id:
        node["otelParentSpanId"] = trace.otel_parent_span_id

    if trace.policy_evaluation is not None:
        node["policyEvaluation"] = {
            "@type": ["PolicyEvaluation", "prov:Activity"],
            "policyId": trace.policy_evaluation.policy_id,
            "policyResult": trace.policy_evaluation.result.value,
            "ruleTriggered": trace.policy_evaluation.rule_triggered,
        }

    if trace.inputs_hash:
        node["used"] = _inputs_entity_id(trace)
    if trace.output_hash:
        node["generated"] = _output_entity_id(trace)

    return node


def _build_entity_nodes(trace: DecisionTrace) -> list[dict[str, Any]]:
    """Map the trace's input/output hashes to PROV entity nodes."""
    nodes: list[dict[str, Any]] = []

    if trace.inputs_hash:
        nodes.append(
            {
                "@id": _inputs_entity_id(trace),
                "@type": ["InputsHash", "prov:Entity"],
                "value": trace.inputs_hash,
            }
        )

    if trace.output_hash:
        output_node: dict[str, Any] = {
            "@id": _output_entity_id(trace),
            "@type": ["OutputHash", "prov:Entity"],
            "value": trace.output_hash,
        }
        # Output was derived from inputs — the canonical PROV chain.
        if trace.inputs_hash:
            output_node["wasDerivedFrom"] = _inputs_entity_id(trace)
        nodes.append(output_node)

    return nodes


def _build_agent_nodes(traces: list[DecisionTrace]) -> list[dict[str, Any]]:
    """One PROV SoftwareAgent node per distinct agent name."""
    seen: dict[str, dict[str, Any]] = {}
    for trace in traces:
        agent_id = _agent_id(trace)
        if agent_id in seen:
            continue
        seen[agent_id] = {
            "@id": agent_id,
            "@type": ["sntl:Agent", "prov:SoftwareAgent"],
            "rdfs:label": trace.agent,
        }
    return list(seen.values())


def build_jsonld_document(traces: list[DecisionTrace]) -> dict[str, Any]:
    """Build the JSON-LD document covering ``traces``.

    Structure:

    .. code-block:: none

        {
          "@context": { ... inlined Sentinel + PROV-O context ... },
          "@graph": [
            { DecisionTrace activity nodes },
            { InputsHash / OutputHash entity nodes },
            { SoftwareAgent nodes }
          ]
        }

    Each trace contributes one activity, two entities (input + output
    hashes, when present), and participates in one shared Agent node
    per distinct ``trace.agent`` name. All IRIs are ``urn:sentinel:*``
    URNs so the document is fully self-contained.
    """
    graph: list[dict[str, Any]] = []
    for trace in traces:
        graph.append(_build_activity_node(trace))
        graph.extend(_build_entity_nodes(trace))
    graph.extend(_build_agent_nodes(traces))

    return {
        "@context": _inline_context(),
        "@graph": graph,
    }


def _validate_with_pyld(document: dict[str, Any]) -> None:
    """Round-trip via pyld.expand + compact; raises on invalid IRI / term."""
    try:
        import pyld.jsonld as _jsonld
    except ImportError as exc:  # pragma: no cover - only when extra missing
        raise ImportError(_MISSING_DEP_MESSAGE) from exc

    # Expansion is the canonical validity check: every term must resolve
    # to a fully-qualified IRI. If any term is undefined, expansion
    # raises. We don't re-compact — the compact form is what we already
    # have, round-tripping here would be noise.
    _jsonld.expand(document)


def render_evidence_jsonld(
    traces: list[DecisionTrace],
    output: str | Path,
) -> Path:
    """Export ``traces`` as a JSON-LD evidence pack at ``output``.

    Validates the emitted document through ``pyld`` before writing,
    so corrupt output can't escape to disk. Raises :class:`ImportError`
    with an actionable message if the ``[jsonld]`` extra isn't installed.
    """
    try:
        import pyld.jsonld  # noqa: F401
    except ImportError as exc:  # pragma: no cover - only when extra missing
        raise ImportError(_MISSING_DEP_MESSAGE) from exc

    import json as _json

    document = build_jsonld_document(traces)
    _validate_with_pyld(document)

    target = Path(output).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_json.dumps(document, indent=2, default=str))
    return target


__all__ = [
    "build_jsonld_document",
    "render_evidence_jsonld",
]
