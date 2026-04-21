"""v3.5 Item 2 — JSON-LD + PROV-O semantic export.

Covers the behaviour from ``docs/architecture/v3.5-item-2-semantic-export.md``:
``comply.export(format='jsonld')`` produces a PROV-O-aligned JSON-LD
document that validates through pyld, preserves OTEL fields when
present, and keeps the NDJSON default path unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pyld")

from sentinel import Sentinel, comply
from sentinel.comply_semantic import (
    build_jsonld_document,
    render_evidence_jsonld,
)

# ---------------------------------------------------------------------------
# Builder shape
# ---------------------------------------------------------------------------


def _make_sentinel_with_traces(count: int = 1) -> Sentinel:
    s = Sentinel(storage=":memory:", signer=None, project="jsonld-export-test")

    @s.trace
    def decide(n: int) -> dict[str, int]:
        return {"approved": True, "amount": n}

    for i in range(count):
        decide(i * 1000)
    return s


def test_build_document_has_context_and_graph() -> None:
    s = _make_sentinel_with_traces(1)
    doc = build_jsonld_document(s.query())

    assert "@context" in doc
    assert "@graph" in doc
    assert isinstance(doc["@graph"], list)
    # Per-trace: 1 activity + 2 entities (input hash, output hash).
    # Plus exactly 1 shared Agent node for "decide".
    # So a single-trace document has 4 nodes.
    assert len(doc["@graph"]) == 4


def test_activity_node_has_decision_trace_and_prov_activity_type() -> None:
    s = _make_sentinel_with_traces(1)
    doc = build_jsonld_document(s.query())

    activities = [
        n for n in doc["@graph"] if "DecisionTrace" in n.get("@type", [])
    ]
    assert len(activities) == 1
    assert "prov:Activity" in activities[0]["@type"]
    # Agent is captured from the function's qualname by default.
    assert activities[0]["agent"].endswith("decide")
    assert activities[0]["project"] == "jsonld-export-test"
    assert activities[0]["wasAssociatedWith"] == f"urn:sentinel:agent:{activities[0]['agent']}"


def test_output_entity_was_derived_from_inputs() -> None:
    """PROV chain: OutputHash wasDerivedFrom InputsHash — the canonical link."""
    s = _make_sentinel_with_traces(1)
    doc = build_jsonld_document(s.query())

    outputs = [n for n in doc["@graph"] if "OutputHash" in n.get("@type", [])]
    inputs = [n for n in doc["@graph"] if "InputsHash" in n.get("@type", [])]
    assert len(outputs) == 1
    assert len(inputs) == 1
    assert outputs[0]["wasDerivedFrom"] == inputs[0]["@id"]


def test_multi_trace_shares_one_agent_node() -> None:
    s = _make_sentinel_with_traces(3)
    doc = build_jsonld_document(s.query())

    agents = [
        n for n in doc["@graph"] if "prov:SoftwareAgent" in n.get("@type", [])
    ]
    assert len(agents) == 1, (
        "three traces for one agent should share one SoftwareAgent node; "
        f"got {len(agents)}"
    )
    assert agents[0]["rdfs:label"].endswith("decide")


def test_fully_populated_trace_maps_all_optional_fields() -> None:
    """A trace with every optional field set round-trips into JSON-LD."""
    from sentinel.core.trace import (
        DecisionTrace,
        PolicyEvaluation,
        PolicyResult,
    )

    t = DecisionTrace(
        project="full",
        agent="fully-populated-agent",
        inputs={"x": 1},
        parent_trace_id="parent-abc",
        precedent_trace_ids=["precedent-1", "precedent-2"],
        signature="Ed25519:deadbeef",
        signature_algorithm="Ed25519",
        tags={"env": "prod", "sector": "banking"},
        otel_trace_id="a" * 32,
        otel_span_id="b" * 16,
        otel_parent_span_id="c" * 16,
    )
    t.policy_evaluation = PolicyEvaluation(
        policy_id="loan-approval-v1",
        policy_version="1.0",
        result=PolicyResult.ALLOW,
        rule_triggered="amount_below_threshold",
    )
    t.complete(output={"decision": "approved"}, latency_ms=42)

    doc = build_jsonld_document([t])
    activity = next(n for n in doc["@graph"] if "DecisionTrace" in n.get("@type", []))

    assert activity["parentTraceId"] == "parent-abc"
    assert activity["precedentTraceIds"] == ["precedent-1", "precedent-2"]
    assert activity["signature"] == "Ed25519:deadbeef"
    assert activity["signatureAlgorithm"] == "Ed25519"
    assert activity["tags"] == {"env": "prod", "sector": "banking"}
    assert activity["otelSpanId"] == "b" * 16
    assert activity["otelParentSpanId"] == "c" * 16
    assert activity["latencyMs"] == 42
    assert activity["policyEvaluation"]["policyId"] == "loan-approval-v1"
    assert activity["policyEvaluation"]["policyResult"] == "ALLOW"


def test_bare_trace_without_hashes_emits_no_entity_nodes() -> None:
    """A DecisionTrace without any inputs/outputs emits the activity alone."""
    from sentinel.core.trace import DecisionTrace

    t = DecisionTrace(project="bare", agent="empty")
    doc = build_jsonld_document([t])

    # Only activity + one shared agent node — no entities.
    types = [n.get("@type") for n in doc["@graph"]]
    has_inputs = any("InputsHash" in ts for ts in types)
    has_outputs = any("OutputHash" in ts for ts in types)
    assert not has_inputs
    assert not has_outputs


def test_trace_with_only_output_entity_skips_inputs() -> None:
    """DecisionTrace with output_hash but no inputs_hash emits only the output entity."""
    from sentinel.core.trace import DecisionTrace

    t = DecisionTrace(project="p", agent="a")
    # No inputs → no inputs_hash; set output_hash manually.
    t.output_hash = "f" * 64

    doc = build_jsonld_document([t])
    inputs_nodes = [n for n in doc["@graph"] if "InputsHash" in n.get("@type", [])]
    output_nodes = [n for n in doc["@graph"] if "OutputHash" in n.get("@type", [])]

    assert inputs_nodes == []
    assert len(output_nodes) == 1
    # Without inputs, PROV wasDerivedFrom is absent (nothing to derive from).
    assert "wasDerivedFrom" not in output_nodes[0]


def test_otel_fields_included_when_present() -> None:
    pytest.importorskip("opentelemetry")
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace import TracerProvider

    otel_trace.set_tracer_provider(TracerProvider())
    tracer = otel_trace.get_tracer("jsonld-test")

    s = Sentinel(storage=":memory:", signer=None)

    @s.trace
    def decide(x: str) -> dict[str, str]:
        return {"r": x}

    with tracer.start_as_current_span("workflow"):
        decide("hello")

    doc = build_jsonld_document(s.query())
    activities = [
        n for n in doc["@graph"] if "DecisionTrace" in n.get("@type", [])
    ]
    assert len(activities) == 1
    assert "otelTraceId" in activities[0]
    assert len(activities[0]["otelTraceId"]) == 32


# ---------------------------------------------------------------------------
# pyld round-trip validation
# ---------------------------------------------------------------------------


def test_emitted_document_expands_via_pyld() -> None:
    """Document is valid JSON-LD: every term resolves under pyld.expand."""
    import pyld.jsonld as jsonld

    s = _make_sentinel_with_traces(2)
    doc = build_jsonld_document(s.query())

    expanded = jsonld.expand(doc)
    flat = str(expanded)

    # PROV-O resolved
    assert "http://www.w3.org/ns/prov#Activity" in flat
    assert "http://www.w3.org/ns/prov#Entity" in flat
    assert "http://www.w3.org/ns/prov#wasDerivedFrom" in flat
    # Sentinel vocabulary resolved
    assert "sentinel-kernel/ontology/v1" in flat


# ---------------------------------------------------------------------------
# File-writing wrapper
# ---------------------------------------------------------------------------


def test_render_evidence_jsonld_writes_valid_file(tmp_path: Path) -> None:
    s = _make_sentinel_with_traces(1)
    out = tmp_path / "evidence.jsonld"

    result = render_evidence_jsonld(s.query(), out)

    assert result == out
    assert out.exists()
    doc = json.loads(out.read_text())
    assert "@context" in doc
    assert "@graph" in doc
    assert len(doc["@graph"]) >= 3


# ---------------------------------------------------------------------------
# comply.export format dispatch
# ---------------------------------------------------------------------------


def test_comply_export_format_jsonld(tmp_path: Path) -> None:
    s = _make_sentinel_with_traces(1)
    out = tmp_path / "evidence.jsonld"

    comply.export(s, out, format="jsonld")

    doc = json.loads(out.read_text())
    assert "@context" in doc
    assert "@graph" in doc


def test_comply_export_unknown_format_raises() -> None:
    s = _make_sentinel_with_traces(1)

    with pytest.raises(ValueError, match="unknown evidence-pack format"):
        comply.export(s, "/tmp/ignored.bin", format="rdfxml")


def test_comply_export_pdf_remains_default(tmp_path: Path) -> None:
    """NDJSON-era callers calling export() with no format= still get PDF."""
    pytest.importorskip("reportlab")
    s = _make_sentinel_with_traces(1)

    # Default format is "pdf" (back-compat); produces a real PDF.
    out = tmp_path / "evidence.pdf"
    comply.export(s, out)
    assert out.exists()
    assert out.read_bytes()[:4] == b"%PDF"
